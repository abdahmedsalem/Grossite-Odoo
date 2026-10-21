"""Read-only verification of actual loaded modules and their standard structure.

Run via `odoo shell`; writes only a JSON report in /tmp and rolls back its cursor.
Optional legacy descriptors: /tmp/architecture-legacy-before.json.
"""
import ast
import csv
import hashlib
import inspect
import json
from pathlib import Path
from lxml import etree
from odoo.modules.module import get_module_path

custom = ['base_industry_data','food_distribution','food_distribution_quality','food_distribution_planning']
result = {'database':env.cr.dbname, 'modules':{}, 'checks':[], 'legacy_field_comparison':[]}
result['legacy_model_comparison']=[]


def check(name, passed, evidence):
    result['checks'].append({'name':name,'passed':bool(passed),'evidence':evidence})


for name in custom:
    root = Path(get_module_path(name, display_warning=False) or '/missing')
    manifest = ast.literal_eval((root / '__manifest__.py').read_text(encoding='utf-8'))
    record = env['ir.module.module'].search([('name','=',name)],limit=1)
    module_result = {'path':str(root),'version':manifest['version'],'state':record.state,
                     'python_files':0,'xml_files':0,'dependencies':[], 'data_defining_manual_models':[],
                     'files_sha256':{}, 'model_classes':[]}
    result['modules'][name] = module_result
    check(name+':loaded_from_custom_addons',root.parent==Path('/mnt/extra-addons'),str(root))
    check(name+':installed',record.state=='installed',record.state)
    check(name+':manifest_version',manifest['version'].startswith('19.0.'),manifest['version'])
    for path in root.rglob('*.py'):
        if '__pycache__' in path.parts:
            continue
        tree = ast.parse(path.read_text(encoding='utf-8'),filename=str(path))
        module_result['python_files'] += 1
        module_result['files_sha256'][str(path.relative_to(root))] = hashlib.sha256(path.read_bytes()).hexdigest()
        for node in tree.body:
            if isinstance(node,ast.ClassDef):
                settings = {}
                for item in node.body:
                    if isinstance(item,ast.Assign) and len(item.targets)==1 and isinstance(item.targets[0],ast.Name) and item.targets[0].id in ('_name','_inherit'):
                        settings[item.targets[0].id]=ast.literal_eval(item.value)
                if settings:
                    module_result['model_classes'].append({'file':str(path.relative_to(root)),'class':node.name,**settings})
                    check(name+':model_in_models:'+node.name,'models' in path.relative_to(root).parts,str(path.relative_to(root)))
    init = ast.parse((root/'__init__.py').read_text())
    if module_result['model_classes']:
        imported = {alias.name for node in init.body if isinstance(node,ast.ImportFrom) for alias in node.names}
        check(name+':models_imported','models' in imported,sorted(imported))
        model_init=ast.parse((root/'models/__init__.py').read_text())
        loaded={alias.name for node in model_init.body if isinstance(node,ast.ImportFrom) for alias in node.names}
        model_files={p.stem for p in (root/'models').glob('*.py') if p.name!='__init__.py'}
        check(name+':model_files_imported',model_files<=loaded,{'files':sorted(model_files),'imports':sorted(loaded)})
    listed = manifest.get('data',[])+manifest.get('demo',[])
    check(name+':manifest_files_exist',all((root/f).is_file() for f in listed),listed)
    for relative in listed:
        path=root/relative
        if path.suffix=='.xml':
            module_result['xml_files']+=1
            tree=etree.parse(str(path))
            for node in tree.iter('record'):
                if node.get('model') in ('ir.model','ir.model.fields'):
                    module_result['data_defining_manual_models'].append({'file':relative,'id':node.get('id')})
        elif path.suffix=='.csv':
            with path.open(encoding='utf-8',newline='') as stream:
                rows=list(csv.DictReader(stream))
            if path.name=='ir.model.access.csv':
                check(name+':acl_in_security',path.parent.name=='security',relative)
                for row in rows:
                    for column in ('model_id:id','group_id:id'):
                        reference=row.get(column)
                        if reference:
                            full=reference if '.' in reference else name+'.'+reference
                            check(name+':acl_reference:'+row['id']+':'+column,
                                  bool(env.ref(full,raise_if_not_found=False)),full)
        module_result['files_sha256'][relative]=hashlib.sha256(path.read_bytes()).hexdigest()
    check(name+':no_xml_manual_schema',not module_result['data_defining_manual_models'],module_result['data_defining_manual_models'])
    for dependency in manifest.get('depends',[]):
        installed=env['ir.module.module'].search([('name','=',dependency)],limit=1)
        dep_path=get_module_path(dependency,display_warning=False)
        dep={'name':dependency,'path':dep_path,'state':installed.state if installed else None}
        module_result['dependencies'].append(dep)
        check(name+':dependency:'+dependency,bool(dep_path) and installed.state=='installed',dep)

model_names=['x_nutritional_facts','x_product_template_ingredients','x_product_template_nutritional_fact',
             'food.quality.point','food.production.forecast']
result['runtime_models']=[]
for name in model_names:
    model=env[name]
    metadata=env['ir.model']._get(name)
    classes=[{'module':cls.__module__,'file':inspect.getsourcefile(cls)}
             for cls in type(model).__mro__ if cls.__module__.startswith('odoo.addons.food_distribution')]
    info={'name':name,'state':metadata.state,'custom_factory_model':bool(model._custom),
          'table':model._table,'python_classes':classes}
    result['runtime_models'].append(info)
    check('runtime:'+name+':python_model',metadata.state=='base' and not model._custom and bool(classes),info)

mapping=ast.literal_eval(Path('/mnt/extra-addons/food_distribution/data/legacy_field_map.txt').read_text())
for alias,model,name in mapping:
    field=env['ir.model.fields']._get(model,name)
    resolved=env.ref('food_distribution.'+alias,raise_if_not_found=False)
    check('runtime:'+model+'.'+name+':base_field',field.state=='base' and not env[model]._fields[name].manual,
          {'state':field.state,'modules':field.modules})
    check('runtime:'+alias+':legacy_xmlid',resolved==field,{'field_id':field.id,'alias_field_id':resolved.id if resolved else None})

views=env['ir.ui.view'].search([('id','in',env['ir.model.data'].search([
    ('module','in',custom),('model','=','ir.ui.view')]).mapped('res_id'))])
for view in views:
    try:
        view._check_xml()
        check('view:'+str(view.id),True,{'name':view.name,'model':view.model})
    except Exception as error:
        check('view:'+str(view.id),False,{'name':view.name,'error':str(error)})

legacy_path=Path('/tmp/architecture-legacy-before.json')
if legacy_path.exists():
    legacy=json.loads(legacy_path.read_text())
    for name,expected in legacy['models'].items():
        model=env[name]
        actual={'table':model._table,'rec_name':model._rec_name,'order':model._order}
        differences={key:{'legacy':expected[key],'python':value} for key,value in actual.items() if expected[key]!=value}
        result['legacy_model_comparison'].append({'model':name,'differences':differences})
    for expected in legacy['fields']:
        field=env[expected['model']]._fields[expected['name']]
        actual={'type':field.type,'required':bool(field.required),'readonly':bool(field.readonly),
            'copy':bool(field.copy),'store':bool(field.store),'translate':bool(getattr(field,'translate',False)),
            'related':list(field.related or ()),'comodel':getattr(field,'comodel_name',None),
            'inverse_name':getattr(field,'inverse_name',None),'ondelete':getattr(field,'ondelete',None),
            'tracking':bool(getattr(field,'tracking',False))}
        differences={key:{'legacy':expected[key],'python':value} for key,value in actual.items() if expected[key]!=value}
        result['legacy_field_comparison'].append({'model':expected['model'],'field':expected['name'],'differences':differences})

result['architecture_passed']=all(item['passed'] for item in result['checks'])
result['legacy_field_semantics_passed']=not any(item['differences'] for item in result['legacy_field_comparison']) if legacy_path.exists() else None
result['legacy_model_semantics_passed']=not any(item['differences'] for item in result['legacy_model_comparison']) if legacy_path.exists() else None
result['checks_count']=len(result['checks'])
env.cr.rollback()
Path('/tmp/standard-architecture-report.json').write_text(json.dumps(result,indent=2,default=str),encoding='utf-8')
print(json.dumps({'architecture_passed':result['architecture_passed'],'checks':len(result['checks']),
                  'legacy_field_semantics_passed':result['legacy_field_semantics_passed'],
                  'legacy_differences':[item for item in result['legacy_field_comparison'] if item['differences']]}),flush=True)
assert result['architecture_passed'], 'Standard architecture checks failed'
