"""Adapt supplied XML resources; run inside the isolated preview container."""
import ast
from pathlib import Path
import shutil
from lxml import etree as E

original = Path('/mnt/original-food')
target = Path('/mnt/extra-addons/food_distribution')
mapping = {
    'ir_ui_view.xml': 'views/nutritional_facts_views.xml',
    'ir_actions_act_window.xml': 'views/nutritional_facts_actions.xml',
    'ir_ui_menu.xml': 'views/nutritional_facts_menus.xml',
    'ir_default.xml': 'data/ir_default.xml',
}
for filename, destination in mapping.items():
    shutil.copyfile(original / 'data' / filename, target / destination)

models = {r.get('id'): r.findtext("field[@name='model']")
          for r in E.parse(str(original / 'data/ir_model.xml')).iter('record')}
models.update({'product.model_product_template': 'product.template',
               'base.model_res_company': 'res.company', 'base_setup.model_res_config_settings': 'res.config.settings'})
aliases = []
for filename in ('ir_model_fields.xml', 'res_config_settings.xml'):
    for record in E.parse(str(original / 'data' / filename)).iter('record'):
        if record.get('model') == 'ir.model.fields':
            model_id = record.find("field[@name='model_id']").get('ref')
            aliases.append((record.get('id'), models[model_id], record.findtext("field[@name='name']")))
(target / 'data/legacy_field_map.txt').write_text(repr(aliases) + '\n')
default_file = target / 'data/ir_default.xml'
default_file.write_text(default_file.read_text().replace('field_x_nutritional_facts_active', 'field_x_nutritional_facts__x_active'))

view = E.parse(str(target / 'views/nutritional_facts_views.xml'))
page = view.find(".//page[@name='label']")
page.set('invisible', 'not x_food_labels_enabled')
page.addprevious(E.Element('field', name='x_food_labels_enabled', invisible='1'))
# A related non-stored sequence must not be used as an SQL ordering expression.
for node in view.xpath(".//field[@name='x_nutritional_fact_ids']/list"):
    node.set('default_order', 'food_sort_sequence, x_per_100g desc, id')
    node.insert(0, E.Element('field', name='food_sort_sequence', column_invisible='1'))
for node in view.xpath('.//*[@options]'):
    node.set('options', node.get('options').replace(':true', ':True'))
view.write(str(target / 'views/nutritional_facts_views.xml'), encoding='utf-8', xml_declaration=True)

for filename in ('product_category.xml', 'product_template.xml', 'product_product.xml',
                 'mrp_workcenter.xml', 'mrp_bom.xml', 'mrp_bom_line.xml',
                 'mrp_routing_workcenter.xml', 'sale_order_template.xml', 'sale_order_template_line.xml'):
    tree = E.parse(str(original / 'data' / filename))
    # This booking product belongs to an unrelated Enterprise application.
    for record in list(tree.iter('record')):
        if record.get('id', '').startswith('appointment_account_payment.'):
            record.getparent().remove(record)
        # Stock balances are operational data, not a product definition.
        for field in list(record.findall("field[@name='qty_available']")):
            record.remove(field)
    tree.write(str(target / 'demo' / filename), encoding='utf-8', xml_declaration=True)

root = E.Element('odoo')
template = E.SubElement(root, 'template', id='report_food_lot_label')
container = E.SubElement(template, 't', attrib={'t-call': 'web.html_container'})
source_label = E.parse(str(original / 'data/qweb_view.xml')).find(".//record[@id='food_distribution_inherit_report_lot_label']/field[@name='arch']/xpath/t")
for cell in source_label.xpath(".//td[@class='label-main-container']"):
    cell.insert(0, E.Element('t', attrib={'t-set': 'res_company', 't-value': 'o.company_id or env.company'}))
container.append(source_label)
bom_template = E.SubElement(root, 'template', id='report_bom_food_label')
E.SubElement(bom_template, 't', attrib={'t-call': 'food_distribution.report_food_lot_label'})
E.ElementTree(root).write(str(target / 'report/lot_label_templates.xml'), encoding='utf-8', xml_declaration=True)

paper = E.parse(str(original / 'data/report_paperformat.xml'))
root = paper.getroot()
for record in list(root.findall('record')):
    root.remove(record)
action = E.SubElement(root, 'record', id='action_report_food_lot_label', model='ir.actions.report')
for name, text in [('name','Food & Drinks Label'), ('model','stock.lot'), ('report_type','qweb-pdf'),
                   ('report_name','food_distribution.report_food_lot_label'),
                   ('report_file','food_distribution.report_food_lot_label'), ('binding_type','report')]:
    E.SubElement(action, 'field', name=name).text = text
E.SubElement(action, 'field', name='paperformat_id', ref='report_paperformat_1')
E.SubElement(action, 'field', name='binding_model_id', ref='stock.model_stock_lot')
action = E.SubElement(root, 'record', id='mrp_bom_product_label_action_report', model='ir.actions.report')
for name, text in [('name','Food Product Label'), ('model','mrp.bom'), ('report_type','qweb-pdf'),
                   ('report_name','food_distribution.report_bom_food_label'),
                   ('report_file','food_distribution.report_bom_food_label'), ('binding_type','report')]:
    E.SubElement(action, 'field', name=name).text = text
E.SubElement(action, 'field', name='paperformat_id', ref='report_paperformat_1')
E.SubElement(action, 'field', name='binding_model_id', ref='mrp.model_mrp_bom')
paper.write(str(target / 'report/paperformat.xml'), encoding='utf-8', xml_declaration=True)

guide = E.parse(str(original / 'data/knowledge_article.xml')).find(".//template[@id='welcome_article_body']")
guide_html = ''.join(E.tostring(child, encoding='unicode', method='html') for child in guide)
guide_html = '<!doctype html><html lang="en"><meta charset="utf-8"><title>Food Distribution Guide</title><style>body{font:16px system-ui;max-width:960px;margin:40px auto;padding:24px;line-height:1.6}img{max-width:100%}</style><h1>Food Distribution Community</h1><p>Community edition: use native Sales, Purchase, Inventory, Manufacturing and Invoicing. The original reference guide below also describes Enterprise features; see the migration coverage document for remaining differences.</p>' + guide_html + '</html>'
(target / 'static/description/guide.html').write_text(guide_html, encoding='utf-8')

# Preserve custom units without overwriting native standard units on installation.
units = E.parse(str(original / 'data/uom_uom.xml'))
for record in list(units.iter('record')):
    if '.' in record.get('id', ''):
        record.getparent().remove(record)
units.write(str(target / 'data/uom_uom.xml'), encoding='utf-8', xml_declaration=True)

# Reuse OCA questions and inspections; only map the original manufacturing points.
quality_root = E.Element('odoo', noupdate='1')
for unit_id, name in [('uom_ph', 'pH'), ('uom_celsius', 'Celsius')]:
    record = E.SubElement(quality_root, 'record', id=unit_id, model='uom.uom')
    E.SubElement(record, 'field', name='name').text = name
for point in E.parse(str(original / 'data/quality_point.xml')).iter('record'):
    point_id = point.get('id')
    values = {f.get('name'): f for f in point.findall('field')}
    title = values['title'].text
    test_type = values['test_type_id'].get('ref')
    quantitative = test_type.endswith('test_type_measure')
    test = E.SubElement(quality_root, 'record', id='test_' + point_id, model='qc.test')
    E.SubElement(test, 'field', name='name').text = title
    question = E.SubElement(quality_root, 'record', id='question_' + point_id, model='qc.test.question')
    E.SubElement(question, 'field', name='test', ref='test_' + point_id)
    E.SubElement(question, 'field', name='name').text = title
    E.SubElement(question, 'field', name='type').text = 'quantitative' if quantitative else 'qualitative'
    notes = '\n'.join((values[key].text or '') for key in ('note','failure_message') if key in values)
    E.SubElement(question, 'field', name='notes').text = notes
    if quantitative:
        E.SubElement(question, 'field', name='min_value').text = values['tolerance_min'].text
        E.SubElement(question, 'field', name='max_value').text = values['tolerance_max'].text
        E.SubElement(question, 'field', name='uom_id', ref='uom_ph' if 'pH' in title else 'uom_celsius')
    else:
        for suffix, text, correct in [('ok', 'Verified', 'True'), ('fail', 'Not verified', 'False')]:
            answer = E.SubElement(quality_root, 'record', id='answer_' + point_id + '_' + suffix, model='qc.test.question.value')
            E.SubElement(answer, 'field', name='test_line', ref='question_' + point_id)
            E.SubElement(answer, 'field', name='name').text = text
            E.SubElement(answer, 'field', name='ok', eval=correct)
    bridge = E.SubElement(quality_root, 'record', id=point_id, model='food.quality.point')
    E.SubElement(bridge, 'field', name='name').text = title
    E.SubElement(bridge, 'field', name='test_id', ref='test_' + point_id)
    for key in ('product_ids', 'operation_id', 'component_id'):
        if key in values:
            field = E.fromstring(E.tostring(values[key]))
            if field.get('ref'):
                field.set('ref', 'food_distribution.' + field.get('ref'))
            if field.get('eval'):
                field.set('eval', field.get('eval').replace("ref('", "ref('food_distribution."))
            bridge.append(field)
    if test_type.endswith('test_type_print_label'):
        E.SubElement(bridge, 'field', name='label_step', eval='True')
quality_dir = target.parent / 'food_distribution_quality/demo'
quality_dir.mkdir(exist_ok=True)
E.ElementTree(quality_root).write(str(quality_dir / 'food_quality_points.xml'), encoding='utf-8', xml_declaration=True)

# Manual forecasts replace the source demo forecast inputs, not its Enterprise MPS engine.
from datetime import date, timedelta
forecast_root = E.Element('odoo', noupdate='1')
for product, bom, quantities in [('product_product_12','mrp_bom_2',[220,240,250,260]),
                                  ('product_product_13','mrp_bom_3',[330,360,380,400])]:
    for week, qty in enumerate(quantities):
        start = date.today() + timedelta(days=7 * week)
        row = E.SubElement(forecast_root, 'record', id=f'forecast_{product}_{week}', model='food.production.forecast')
        E.SubElement(row, 'field', name='product_id', ref='food_distribution.' + product)
        E.SubElement(row, 'field', name='bom_id', ref='food_distribution.' + bom)
        E.SubElement(row, 'field', name='date_start').text = str(start)
        E.SubElement(row, 'field', name='date_end').text = str(start + timedelta(days=6))
        E.SubElement(row, 'field', name='quantity').text = str(qty)
forecast_dir = target.parent / 'food_distribution_planning/demo'
forecast_dir.mkdir(exist_ok=True)
E.ElementTree(forecast_root).write(str(forecast_dir / 'forecasts.xml'), encoding='utf-8', xml_declaration=True)

# Original modules remain untouched outside migration/. Remove inactive XML from
# the port so that only the manifest's actual resources remain in its folders.
for module in ('food_distribution', 'base_industry_data'):
    module_dir = target.parent / module
    manifest = ast.literal_eval((module_dir / '__manifest__.py').read_text())
    keep = set(manifest.get('data', []) + manifest.get('demo', []))
    for folder in ('data', 'demo'):
        for path in (module_dir / folder).glob('*.xml'):
            if str(path.relative_to(module_dir)) not in keep:
                path.unlink()
print('SOURCE_ADAPTATION_COMPLETE')
