"""Check IDs, stored data and behavior after replacing XML/manual models by Python."""
import json
from pathlib import Path

assert env.cr.dbname.startswith('food_distribution_architecture_')
before=json.loads(Path('/tmp/architecture-legacy-before.json').read_text())
result={'database':env.cr.dbname,'records':[],'field_ids':[],'duplication':{},'remaining_manual_fields':[]}
for model,snapshot in before['snapshot'].items():
    records=env[model].browse(snapshot['ids']).exists()
    rows=json.loads(json.dumps(records.read(snapshot['columns']),default=str))
    passed=rows==snapshot['rows']
    result['records'].append({'model':model,'ids':snapshot['ids'],'preserved':passed})
for field in before['fields']:
    metadata=env['ir.model.fields']._get(field['model'],field['name'])
    result['field_ids'].append({'model':field['model'],'field':field['name'],
        'same_id':metadata.id==field['field_id'],'state':metadata.state})
for name in before['models']:
    result['remaining_manual_fields'].extend(
        {'model':name,'field':f.name} for f in env['ir.model.fields'].search([('model','=',name),('state','=','manual')]))
food=env['product.template'].browse(before['fixture']['template_id'])
duplicate=food.copy({'name':'ARCHITECTURE Python Duplicate'})
result['duplication']={'ingredients':len(duplicate.x_ingredient_ids),'nutrition':len(duplicate.x_nutritional_fact_ids)}
result['legacy_duplication']=before['legacy_duplication']
result['passed']=(all(item['preserved'] for item in result['records']) and
    all(item['same_id'] and item['state']=='base' for item in result['field_ids']) and
    not result['remaining_manual_fields'] and result['duplication']==before['legacy_duplication'])
env.cr.rollback()
Path('/tmp/architecture-legacy-migration.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps(result),flush=True)
assert result['passed'],'Legacy XML-to-Python migration did not preserve all tested data and semantics'
