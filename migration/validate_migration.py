"""Run in the preview Odoo shell. Never writes to the source/baseline database."""
import hashlib
import json
import os
from pathlib import Path
import psycopg2
from psycopg2 import sql
from odoo import fields

assert env.cr.dbname.startswith('food_distribution_migration_')
baseline = os.environ['BASELINE_DB']
assert baseline.endswith('_baseline') and baseline.startswith('food_distribution_migration_')
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
result = {'database': env.cr.dbname, 'baseline': baseline, 'preservation': [], 'errors': []}
connection = psycopg2.connect(host=os.environ['HOST'], user=os.environ['USER'],
                             password=os.environ['PASSWORD'], dbname=baseline)
connection.set_session(readonly=True)
try:
    with connection.cursor() as cursor:
        for table, columns in tables.items():
            query = sql.SQL('SELECT {} FROM {} ORDER BY id').format(
                sql.SQL(',').join(map(sql.Identifier, columns)), sql.Identifier(table))
            cursor.execute(query)
            before = cursor.fetchall()
            env.cr.execute(query)
            after = {row[0]: row for row in env.cr.fetchall()}
            differences = [row[0] for row in before if after.get(row[0]) != row]
            digest = hashlib.sha256(json.dumps(before, default=str, sort_keys=True).encode()).hexdigest()
            result['preservation'].append({'table': table, 'columns': columns, 'baseline_rows': len(before),
                                          'changed_or_missing_ids': differences, 'baseline_sha256': digest})
            if differences:
                result['errors'].append(f'{table}: baseline records changed: {differences}')
finally:
    connection.close()

# Enable the feature only in the preview clone and prepare a visible example.
env.company.x_module_food_drinks_labels = True
parameters = env['ir.config_parameter'].sudo()
parameters.set_param('web.base.url', 'http://localhost:8074')
parameters.set_param('web.base.url.freeze', 'True')
parameters.set_param('report.url', 'http://127.0.0.1:8069')
fact = env.ref('food_distribution.x_nutritional_facts_1')
ingredient = env['product.template'].search([('name', '=', 'MIGRATION PREVIEW Egg')], limit=1)
if not ingredient:
    ingredient = env['product.template'].create({'name': 'MIGRATION PREVIEW Egg', 'x_is_allergen': True})
item = env['product.product'].search([('name', '=', 'MIGRATION PREVIEW Food')], limit=1)
if not item:
    item = env['product.product'].create({'name': 'MIGRATION PREVIEW Food', 'type': 'consu',
        'is_storable': True, 'tracking': 'lot', 'use_expiration_date': True, 'expiration_time': 30,
        'barcode': '1234567890128', 'x_label_note': 'Keep refrigerated.',
        'x_ingredient_ids': [(0, 0, {'x_ingredient_id': ingredient.id, 'x_share': 6})],
        'x_nutritional_fact_ids': [(0, 0, {'x_nutritional_fact_id': fact.id, 'x_per_100g': 10})]})
lot = env['stock.lot'].search([('product_id', '=', item.id), ('name', '=', 'MIGRATION-PREVIEW-LOT')], limit=1)
if not lot:
    lot = env['stock.lot'].create({'name': 'MIGRATION-PREVIEW-LOT', 'product_id': item.id, 'company_id': env.company.id})
result['preview'] = {'product_template_id': item.product_tmpl_id.id, 'product_id': item.id, 'lot_id': lot.id}

html, _format = env['ir.actions.report']._render_qweb_html('food_distribution.action_report_food_lot_label', [lot.id])
assert b'MIGRATION PREVIEW' in html and b'Keep refrigerated' in html
pdf, _format = env['ir.actions.report']._render_qweb_pdf('food_distribution.action_report_food_lot_label', [lot.id])
assert pdf.startswith(b'%PDF') and len(pdf) > 1000
Path('/tmp/migration-food-label.pdf').write_bytes(pdf)
result['food_label_pdf'] = {'bytes': len(pdf), 'valid_pdf_header': True, 'html_contains_food_data': True}

# Fingerprint custom rows before a full module update; check_update.py compares them.
custom_snapshot = {}
for model, domain, columns in [
    ('product.template', [('id', 'in', item.product_tmpl_id.ids + ingredient.ids)], ['name','x_label_note','x_is_allergen']),
    ('x_product_template_ingredients', [('x_product_template_id','=',item.product_tmpl_id.id)], ['x_product_template_id','x_ingredient_id','x_share']),
    ('x_product_template_nutritional_fact', [('x_product_template_id','=',item.product_tmpl_id.id)], ['x_product_template_id','x_nutritional_fact_id','x_per_100g']),
    ('x_nutritional_facts', [('id','=',fact.id)], ['x_name','x_active','x_unit_id','x_sequence']),
]:
    custom_snapshot[model] = {'domain': domain, 'fields': columns,
                              'rows': env[model].search(domain, order='id').read(columns)}
Path('/tmp/migration-custom-before.json').write_text(json.dumps(custom_snapshot, default=str, sort_keys=True))
env.cr.commit()
Path('/tmp/migration-validation.json').write_text(json.dumps(result, indent=2, default=str))
print(json.dumps({'preservation_tables': len(tables), 'errors': result['errors'], 'food_label_pdf_bytes': len(pdf)}), flush=True)
assert not result['errors'], 'Source data preservation failed'
