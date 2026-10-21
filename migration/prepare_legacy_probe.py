"""Reconstruct the supplied XML models on a disposable pre-migration database."""
import ast
import json
from pathlib import Path
from lxml import etree
from odoo.tools.convert import convert_xml_import

assert env.cr.dbname.startswith('food_distribution_architecture_')
assert env['ir.module.module'].search([('name','=','food_distribution')], limit=1).state == 'uninstalled'
original = Path('/mnt/original-food/data')
def import_xml(path):
    with path.open('rb') as stream:
        convert_xml_import(env, 'food_distribution', stream, {}, mode='init')

for filename in ('ir_model.xml', 'ir_model_fields.xml', 'ir_model_access.xml', 'ir_default.xml'):
    import_xml(original / filename)
tree = etree.parse(str(original / 'res_config_settings.xml'))
root = etree.Element('odoo')
for record in tree.iter('record'):
    if record.get('model') == 'ir.model.fields':
        root.append(record)
temp = Path('/tmp/architecture-legacy-settings-fields.xml')
etree.ElementTree(root).write(str(temp), encoding='utf-8', xml_declaration=True)
import_xml(temp)
mapping = ast.literal_eval(Path('/mnt/extra-addons/food_distribution/data/legacy_field_map.txt').read_text())
descriptors = []
for xmlid, model, name in mapping:
    field = env[model]._fields[name]
    metadata = env['ir.model.fields']._get(model, name)
    descriptors.append({'xmlid': xmlid, 'model': model, 'name': name, 'type': field.type,
        'required': bool(field.required), 'readonly': bool(field.readonly), 'copy': bool(field.copy),
        'store': bool(field.store), 'translate': bool(getattr(field,'translate',False)),
        'related': list(field.related or ()), 'comodel': getattr(field,'comodel_name',None),
        'inverse_name': getattr(field,'inverse_name',None), 'ondelete': getattr(field,'ondelete',None),
        'tracking': bool(getattr(field,'tracking',False)), 'field_id': metadata.id})
fact = env['x_nutritional_facts'].create({'x_name':'ARCHITECTURE Legacy Fact', 'x_sequence':17,
    'x_unit_id': env.ref('uom.product_uom_gram').id})
ingredient = env['product.template'].create({'name':'ARCHITECTURE Legacy Ingredient', 'x_is_allergen':True})
food = env['product.product'].create({'name':'ARCHITECTURE Legacy Food', 'type':'consu',
    'is_storable':True, 'tracking':'lot', 'use_expiration_date':True, 'expiration_time':30,
    'x_label_note':'Legacy storage instructions',
    'x_ingredient_ids':[(0,0,{'x_ingredient_id':ingredient.id,'x_share':7})],
    'x_nutritional_fact_ids':[(0,0,{'x_nutritional_fact_id':fact.id,'x_per_100g':12.5})]})
lot = env['stock.lot'].create({'name':'ARCHITECTURE-LEGACY-LOT','product_id':food.id,'company_id':env.company.id})
warehouse = env['stock.warehouse'].search([('company_id','=',env.company.id)], limit=1)
env['stock.quant']._update_available_quantity(food, warehouse.lot_stock_id, 5, lot_id=lot)
customer = env['res.partner'].create({'name':'ARCHITECTURE Legacy Customer'})
sale = env['sale.order'].create({'partner_id':customer.id,'order_line':[(0,0,{
    'product_id':food.id,'product_uom_qty':2,'price_unit':12})]})
duplicate = food.product_tmpl_id.copy({'name':'ARCHITECTURE Legacy Duplicate'})
result = {'database':env.cr.dbname, 'fields':descriptors,
    'models':{name:{'table':env[name]._table,'rec_name':env[name]._rec_name,'order':env[name]._order,
                    'state':env['ir.model']._get(name).state}
              for name in ('x_nutritional_facts','x_product_template_ingredients','x_product_template_nutritional_fact')},
    'fixture':{'food_id':food.id, 'template_id':food.product_tmpl_id.id, 'ingredient_id':ingredient.id,
               'fact_id':fact.id, 'lot_id':lot.id, 'sale_id':sale.id,
               'ingredient_line_ids':food.x_ingredient_ids.ids,'nutrition_line_ids':food.x_nutritional_fact_ids.ids},
    'legacy_duplication':{'ingredients':len(duplicate.x_ingredient_ids),'nutrition':len(duplicate.x_nutritional_fact_ids)}}
result['all_model_fields'] = {
    model: {name:{'type':field.type,'manual':bool(field.manual),'required':bool(field.required),
                  'copy':bool(field.copy),'readonly':bool(field.readonly),'store':bool(field.store)}
            for name,field in env[model]._fields.items()}
    for model in result['models']
}
snapshot = {}
for model, records, columns in [
    ('product.template',food.product_tmpl_id | ingredient,['name','x_label_note','x_is_allergen']),
    ('x_nutritional_facts',fact,['x_name','x_active','x_sequence','x_unit_id']),
    ('x_product_template_ingredients',food.x_ingredient_ids,['x_product_template_id','x_ingredient_id','x_share']),
    ('x_product_template_nutritional_fact',food.x_nutritional_fact_ids,['x_product_template_id','x_nutritional_fact_id','x_per_100g']),
    ('stock.lot',lot,['name','product_id','expiration_date']),
    ('sale.order',sale,['name','partner_id','state','amount_total']),
]:
    snapshot[model]={'ids':records.ids,'columns':columns,'rows':records.read(columns)}
result['snapshot']=snapshot
env.cr.commit()
Path('/tmp/architecture-legacy-before.json').write_text(json.dumps(result, indent=2, default=str),encoding='utf-8')
print(json.dumps({'legacy_fields':len(descriptors),'legacy_duplication':result['legacy_duplication'],
                  'models':result['models']}),flush=True)
