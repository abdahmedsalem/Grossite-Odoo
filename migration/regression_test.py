"""Reuse the audit's native Community workflows after installing the port."""
import ast
import json
from pathlib import Path
import traceback
from odoo import fields

assert env.cr.dbname.startswith('food_distribution_migration_')
source = ast.parse(Path('/tmp/food_audit_source.py').read_text(encoding='utf-8'))
names = {'RollbackTest','test','product','validate_picking','sale_delivery','purchase_receipt',
         'lot_expiry','manufacturing','invoice_posting','linked_food_workflow','community_user_menu_access'}
nodes = [node for node in source.body if isinstance(node, (ast.FunctionDef, ast.ClassDef)) and node.name in names]
report = {'tests': []}
exec(compile(ast.Module(body=nodes, type_ignores=[]), '<audit-workflows>', 'exec'))
for name, function in [
    ('community_sale_and_delivery',sale_delivery), ('community_purchase_and_receipt',purchase_receipt),
    ('community_lot_and_expiration',lot_expiry), ('community_manufacturing',manufacturing),
    ('community_invoice_posting',invoice_posting),
    ('community_food_purchase_to_sale_invoice_same_lot',linked_food_workflow),
    ('community_non_admin_business_menu_access',community_user_menu_access),
]:
    test(name, function)
env.cr.rollback()
Path('/tmp/migration-regression-results.json').write_text(json.dumps(report, indent=2, default=str))
assert all(item['status']=='passed' for item in report['tests']), 'Native Community regression detected'
