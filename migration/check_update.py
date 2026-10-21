import json
from pathlib import Path

assert env.cr.dbname.startswith('food_distribution_migration_')
before = json.loads(Path('/tmp/migration-custom-before.json').read_text())
results = []
for model, data in before.items():
    rows = env[model].search(data['domain'], order='id').read(data['fields'])
    passed = json.loads(json.dumps(rows, default=str, sort_keys=True)) == data['rows']
    results.append({'model': model, 'rows': len(rows), 'preserved': passed})
    assert passed, f'Custom data changed during module update: {model}'
Path('/tmp/migration-update-validation.json').write_text(json.dumps(results, indent=2))
print('UPGRADE_CUSTOM_DATA_PRESERVED', len(results), flush=True)
