"""Fingerprint original business rows around deployment, without writing to Odoo."""
import hashlib
import json
import os
from pathlib import Path
import psycopg2
from psycopg2 import sql

database = os.environ.get('CHECK_DB', 'food_distribution')
assert database == 'food_distribution', 'Unexpected deployment database'
mode = os.environ['CHECK_MODE']
assert mode in ('before', 'after')
tables = {
    'res_company': ['id','name','partner_id','currency_id'],
    'res_partner': ['id','name','parent_id','company_id','active'],
    'product_template': ['id','name','type','list_price','active','uom_id'],
    'product_product': ['id','product_tmpl_id','active','default_code'],
    'sale_order': ['id','name','partner_id','state','amount_total','currency_id'],
    'sale_order_line': ['id','order_id','product_id','product_uom_qty','price_unit','qty_delivered','qty_invoiced'],
    'purchase_order': ['id','name','partner_id','state','amount_total','currency_id'],
    'purchase_order_line': ['id','order_id','product_id','product_qty','price_unit','qty_received'],
    'stock_quant': ['id','product_id','location_id','lot_id','quantity','reserved_quantity','company_id'],
    'stock_move': ['id','product_id','state','product_uom_qty','location_id','location_dest_id'],
    'stock_lot': ['id','name','product_id','company_id'],
    'mrp_production': ['id','name','product_id','product_qty','state','bom_id'],
    'account_move': ['id','name','partner_id','state','amount_total','currency_id'],
    'account_move_line': ['id','move_id','account_id','debit','credit','balance'],
    'uom_uom': ['id','name','relative_factor','relative_uom_id'],
}
connection = psycopg2.connect(host=os.environ['HOST'], user=os.environ['USER'],
    password=os.environ['PASSWORD'], dbname=database)
connection.set_session(readonly=True)
snapshot = {}
with connection, connection.cursor() as cursor:
    for table, columns in tables.items():
        cursor.execute(sql.SQL('SELECT {} FROM {} ORDER BY id').format(
            sql.SQL(',').join(map(sql.Identifier, columns)), sql.Identifier(table)))
        snapshot[table] = json.loads(json.dumps(cursor.fetchall(), default=str, sort_keys=True))
connection.close()
baseline_file = Path('/tmp/food-live-preservation-before.json')
if mode == 'before':
    baseline_file.write_text(json.dumps(snapshot, sort_keys=True))
    print(json.dumps({'baseline_saved': True, 'tables': len(snapshot)}))
else:
    baseline = json.loads(baseline_file.read_text())
    results = []
    for table, rows in baseline.items():
        current = {row[0]: row for row in snapshot[table]}
        differences = [row[0] for row in rows if current.get(row[0]) != row]
        results.append({'table': table, 'original_rows': len(rows),
            'changed_or_missing_ids': differences, 'new_rows': len(current)-len(rows),
            'original_sha256': hashlib.sha256(json.dumps(rows, sort_keys=True).encode()).hexdigest()})
    output = {'database': database, 'results': results,
              'passed': not any(row['changed_or_missing_ids'] for row in results)}
    Path('/tmp/migration-live-preservation.json').write_text(json.dumps(output, indent=2))
    print(json.dumps({'preservation_passed': output['passed'], 'tables': len(results)}))
    assert output['passed'], 'Existing business data changed during deployment'
