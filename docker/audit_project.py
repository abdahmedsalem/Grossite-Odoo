"""Run with `odoo shell` against a disposable food_distribution_audit_* clone.

Reads module sources, inspects the installed registry, runs ORM workflows inside
rolled-back savepoints, and writes /tmp/food_distribution_audit_results.json.
Never point this script at a production database.
"""

import ast
from copy import deepcopy
from collections import Counter
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import re
import shutil
import traceback
import xml.etree.ElementTree as ET

from odoo import fields
from odoo.exceptions import UserError
from odoo.modules.module import get_module_path
from odoo.tools.convert import convert_file
from odoo.tools.template_inheritance import apply_inheritance_specs
from lxml import etree


assert env.cr.dbname.startswith("food_distribution_audit_"), "Audit clone required"
env = env(context=dict(env.context, tracking_disable=True, mail_create_nolog=True,
                       mail_notify_force_send=False, no_reset_password=True))
report = {
    "generated_utc": datetime.now(timezone.utc).isoformat(),
    "database": env.cr.dbname,
    "odoo_version": __import__("odoo").release.version,
    "modules": {}, "tests": [],
    "limits": [
        "Food Distribution and Industry Base are not installed in the source database.",
        "Business smoke tests cover installed Community apps, not absent Enterprise functionality.",
        "ORM tests run as the shell superuser and do not validate normal-user permissions or browser rendering.",
        "No migration has been performed; no before/after migration equivalence is established.",
        "No payments, emails, scheduled jobs or external services are invoked by the test script.",
    ],
}

source_store = Path('/var/lib/odoo/filestore/food_distribution')
clone_store = source_store.with_name(env.cr.dbname)
if source_store.exists() and not clone_store.exists():
    shutil.copytree(source_store, clone_store)
report['filestore_cloned'] = clone_store.exists()

installed = env['ir.module.module'].search([('state', '=', 'installed')])
report['installed_modules'] = sorted(installed.mapped('name'))
report['source_configuration'] = {
    'company_name': env.company.name,
    'country': env.company.country_id.code,
    'currency': env.company.currency_id.name,
    'chart_template': env.company.chart_template,
    'account_count': env['account.account'].search_count([]),
    'journal_types': dict(Counter(env['account.journal'].search([]).mapped('type'))),
}

all_defined = set()
parsed = {}
manifests = {}
for module in ('base_industry_data', 'food_distribution'):
    root = Path('/mnt/extra-addons') / module
    manifest = ast.literal_eval((root / '__manifest__.py').read_text(encoding='utf-8'))
    manifests[module] = manifest
    for section in ('data', 'demo'):
        for relative in manifest.get(section, []):
            path = root / relative
            tree = ET.parse(path)
            parsed[(module, relative)] = tree
            for node in tree.iter():
                xmlid = node.get('id')
                if xmlid:
                    all_defined.add(xmlid if '.' in xmlid else f'{module}.{xmlid}')


def field_values(record):
    return {f.get('name'): (f.get('ref') or f.get('eval') or ''.join(f.itertext()).strip())
            for f in record.findall('field')}


for module, manifest in manifests.items():
    root = Path('/mnt/extra-addons') / module
    result = {
        'license': manifest.get('license'),
        'dependencies': [], 'files': [], 'custom_models': [], 'custom_fields': [],
        'missing_models': [], 'missing_fields': [], 'unresolved_references': [],
        'executables': [], 'views': [], 'access_rules': [], 'relocation_plan': [],
        'parse_errors': [], 'resources_missing': [], 'node_counts': {}, 'function_compatibility': [],
    }
    report['modules'][module] = result
    for dep in manifest.get('depends', []):
        dep_path = get_module_path(dep, display_warning=False)
        dep_manifest = {}
        if dep_path:
            dep_file = Path(dep_path) / '__manifest__.py'
            if dep_file.exists():
                dep_manifest = ast.literal_eval(dep_file.read_text(encoding='utf-8'))
        dependency = env['ir.module.module'].search([('name', '=', dep)], limit=1)
        result['dependencies'].append({
            'name': dep, 'code_present': bool(dep_path),
            'state': dependency.state if dependency else 'not_registered',
            'license': dep_manifest.get('license'),
        })
    for section in ('data', 'demo'):
        for relative in manifest.get(section, []):
            tree = parsed[(module, relative)]
            path = root / relative
            records = list(tree.iter('record'))
            counts = dict(Counter(r.get('model') for r in records))
            functions = list(tree.iter('function'))
            result['files'].append({
                'path': relative, 'section': section, 'records': len(records),
                'models': counts, 'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
            })
            for tag in ('record', 'template', 'menuitem', 'function'):
                result['node_counts'][tag] = result['node_counts'].get(tag, 0) + len(list(tree.iter(tag)))
            for node in tree.iter():
                resource = node.get('file')
                if resource and '/' in resource:
                    resource_module, resource_path = resource.split('/', 1)
                    resource_root = get_module_path(resource_module, display_warning=False)
                    if not resource_root or not (Path(resource_root) / resource_path).is_file():
                        result['resources_missing'].append({'file': relative, 'resource': resource})
            # Move whole files only; mixed configuration files retain their order.
            folder = 'data'
            if section == 'demo':
                folder = 'demo'
            elif (records or list(tree.iter('menuitem'))) and set(counts) <= {'ir.ui.view', 'ir.ui.menu', 'ir.actions.act_window'} and not functions:
                folder = 'views'
            elif records and set(counts) <= {'ir.model.access', 'ir.rule', 'res.groups'} and not functions:
                folder = 'security'
            destination = f'{folder}/{path.name}'
            result['relocation_plan'].append({
                'source': relative, 'destination': destination,
                'section': section, 'preserve_manifest_position': True,
            })
            for record in records:
                model = record.get('model')
                values = field_values(record)
                identity = {'file': relative, 'id': record.get('id'), 'model': model}
                if model == 'ir.model':
                    result['custom_models'].append(dict(identity, fields=values))
                elif model == 'ir.model.fields':
                    result['custom_fields'].append(dict(identity, fields=values))
                elif model == 'ir.ui.view':
                    result['views'].append(dict(identity, target_model=values.get('model'),
                                                inherit_id=values.get('inherit_id')))
                elif model in ('ir.model.access', 'ir.rule'):
                    result['access_rules'].append(dict(identity, fields=values))
                elif model in ('base.automation', 'ir.actions.server'):
                    result['executables'].append(dict(identity, fields=values))
                if model not in env:
                    result['missing_models'].append(identity)
                else:
                    for field in record.findall('field'):
                        name = field.get('name')
                        if name not in env[model]._fields:
                            result['missing_fields'].append(dict(identity, field=name))
            for function in functions:
                function_model = function.get('model')
                method = function.get('name')
                result['executables'].append({
                    'file': relative, 'model': function_model,
                    'method': method, 'kind': 'xml_function',
                })
                result['function_compatibility'].append({
                    'file': relative, 'model': function_model, 'method': method,
                    'model_available': function_model in env,
                    'method_available': function_model in env and callable(getattr(env[function_model], method, None)),
                })
            refs = set()
            for node in tree.iter():
                if node.get('ref'):
                    refs.add(node.get('ref'))
                for attr in ('eval', 'context', 'domain'):
                    refs.update(re.findall(r"\bref\(['\"]([^'\"]+)['\"]\)", node.get(attr, '')))
                for attr in ('t-call', 't-inherit'):
                    if node.get(attr):
                        refs.add(node.get(attr))
                if node.get('name') != 'serial_prefix_format':
                    refs.update(re.findall(r'%\(([^)]+)\)[ds]', node.text or ''))
                if node.tag == 'menuitem':
                    refs.update(node.get(attr) for attr in ('parent', 'action') if node.get(attr))
            for reference in sorted(refs):
                full = reference if '.' in reference else f'{module}.{reference}'
                if full not in all_defined and not env.ref(full, raise_if_not_found=False):
                    result['unresolved_references'].append({'file': relative, 'xmlid': full})


class RollbackTest(Exception):
    pass


def test(name, function):
    entry = {'name': name}
    try:
        with env.cr.savepoint():
            entry['evidence'] = function()
            raise RollbackTest()
    except RollbackTest:
        entry['status'] = 'passed'
    except Exception as error:
        entry.update(status='failed', error=f'{type(error).__name__}: {error}',
                     traceback=traceback.format_exc())
    env.invalidate_all()
    report['tests'].append(entry)
    print(f"AUDIT_TEST {name}: {entry['status']}", flush=True)


def product(name, **extra):
    return env['product.product'].create(dict(
        name='AUDIT ' + name, type='consu', is_storable=True,
        list_price=12.0, standard_price=5.0, **extra))


def validate_picking(picking):
    picking.action_assign()
    for move in picking.move_ids:
        move.quantity = move.product_uom_qty
        move.picked = True
    action = picking.with_context(skip_backorder=True).button_validate()
    assert picking.state == 'done', f'Picking not done: {picking.state}; {action}'


def sale_delivery():
    item = product('sale')
    warehouse = env['stock.warehouse'].search([('company_id', '=', env.company.id)], limit=1)
    env['stock.quant']._update_available_quantity(item, warehouse.lot_stock_id, 10.0)
    customer = env['res.partner'].create({'name': 'AUDIT Customer'})
    order = env['sale.order'].create({
        'partner_id': customer.id,
        'order_line': [(0, 0, {'product_id': item.id, 'product_uom_qty': 2.0, 'price_unit': 12.0})],
    })
    order.action_confirm()
    assert order.state == 'sale'
    pickings = order.picking_ids.filtered(lambda p: p.state not in ('done', 'cancel'))
    assert pickings, 'No delivery created'
    for picking in pickings:
        validate_picking(picking)
    assert order.order_line.qty_delivered == 2.0
    return {'sale_state': order.state, 'delivery_states': pickings.mapped('state'),
            'quantity_delivered': order.order_line.qty_delivered}


def purchase_receipt():
    item = product('purchase')
    supplier = env['res.partner'].create({'name': 'AUDIT Supplier'})
    order = env['purchase.order'].create({
        'partner_id': supplier.id,
        'order_line': [(0, 0, {'product_id': item.id, 'product_qty': 3.0, 'price_unit': 5.0,
                               'date_planned': fields.Datetime.now()})],
    })
    order.button_confirm()
    assert order.state == 'purchase'
    pickings = order.picking_ids.filtered(lambda p: p.state not in ('done', 'cancel'))
    assert pickings, 'No receipt created'
    for picking in pickings:
        validate_picking(picking)
    assert order.order_line.qty_received == 3.0
    return {'purchase_state': order.state, 'receipt_states': pickings.mapped('state'),
            'quantity_received': order.order_line.qty_received}


def lot_expiry():
    item = product('expiry', tracking='lot', use_expiration_date=True, expiration_time=10,
                   alert_time=2, removal_time=1)
    lot = env['stock.lot'].create({'name': 'AUDIT-LOT-001', 'product_id': item.id,
                                  'company_id': env.company.id})
    assert lot.expiration_date, 'No expiration date computed'
    assert lot.alert_date and lot.removal_date
    assert lot.alert_date < lot.expiration_date
    warehouse = env['stock.warehouse'].search([('company_id', '=', env.company.id)], limit=1)
    env['stock.quant']._update_available_quantity(item, warehouse.lot_stock_id, 4, lot_id=lot)
    quants = env['stock.quant'].search([('product_id', '=', item.id), ('lot_id', '=', lot.id)])
    assert sum(quants.mapped('quantity')) == 4
    return {'tracking': item.tracking, 'expiration_date': str(lot.expiration_date),
            'alert_date': str(lot.alert_date), 'lot_quantity': sum(quants.mapped('quantity'))}


def manufacturing():
    component = product('component')
    finished = product('finished')
    warehouse = env['stock.warehouse'].search([('company_id', '=', env.company.id)], limit=1)
    env['stock.quant']._update_available_quantity(component, warehouse.lot_stock_id, 10.0)
    bom = env['mrp.bom'].create({
        'product_tmpl_id': finished.product_tmpl_id.id, 'product_qty': 1,
        'bom_line_ids': [(0, 0, {'product_id': component.id, 'product_qty': 2})],
    })
    production = env['mrp.production'].create({
        'product_id': finished.id, 'product_qty': 2, 'bom_id': bom.id,
    })
    production.action_confirm()
    production.action_assign()
    production.qty_producing = 2
    for move in production.move_raw_ids:
        move.quantity = move.product_uom_qty
        move.picked = True
    production.button_mark_done()
    assert production.state == 'done', f'Manufacturing state: {production.state}'
    assert production.qty_produced == 2
    return {'production_state': production.state, 'quantity_produced': production.qty_produced,
            'component_moves': production.move_raw_ids.mapped('state')}


def invoice_posting():
    # Explicit synthetic accounts make this a workflow test, not a test of the
    # production chart of accounts or country-specific fiscal compliance.
    company = env.company
    def account(code, account_type):
        vals = {'name': 'AUDIT ' + account_type, 'code': code, 'account_type': account_type}
        if 'company_ids' in env['account.account']._fields:
            vals['company_ids'] = [(6, 0, company.ids)]
        else:
            vals['company_id'] = company.id
        if account_type == 'asset_receivable':
            vals['reconcile'] = True
        return env['account.account'].create(vals)
    revenue = account('AUDITREV01', 'income')
    receivable = account('AUDITREC01', 'asset_receivable')
    journal = env['account.journal'].create({'name': 'AUDIT Sales', 'code': 'AUDT1',
        'type': 'sale', 'company_id': company.id, 'default_account_id': revenue.id})
    customer = env['res.partner'].create({'name': 'AUDIT Invoice customer',
        'property_account_receivable_id': receivable.id})
    invoice = env['account.move'].create({
        'move_type': 'out_invoice', 'partner_id': customer.id,
        'journal_id': journal.id, 'invoice_date': fields.Date.today(),
        'invoice_line_ids': [(0, 0, {'name': 'AUDIT goods', 'quantity': 2,
            'price_unit': 12, 'account_id': revenue.id, 'tax_ids': [(5, 0, 0)]})],
    })
    invoice.action_post()
    assert invoice.state == 'posted'
    assert invoice.amount_total == 24
    assert abs(sum(invoice.line_ids.mapped('balance'))) < 0.00001
    return {'state': invoice.state, 'amount_total': invoice.amount_total,
            'balanced': True, 'uses_synthetic_accounts': True}


def source_install_blocked():
    module = env['ir.module.module'].search([('name', '=', 'food_distribution')], limit=1)
    assert module and module.state == 'uninstalled'
    try:
        module.button_immediate_install()
    except UserError as error:
        message = str(error)
        assert 'module' in message.lower(), message
        return {'expected_installation_rejection': message}
    raise AssertionError('Original Enterprise module unexpectedly installed')


def relocation_integrity():
    checked = 0
    for module, data in report['modules'].items():
        destinations = set()
        for planned in data['relocation_plan']:
            destination = planned['destination']
            assert destination not in destinations, f'Destination collision: {destination}'
            destinations.add(destination)
            checked += 1
        # Each manifest item retains the same XML bytes, IDs and sequence in a
        # relocation-only plan. Does not claim an ORM/Python migration was tested.
        original = [(s, p) for s in ('data', 'demo') for p in manifests[module].get(s, [])]
        planned = [(p['section'], p['source']) for p in data['relocation_plan']]
        assert original == planned
    return {'manifest_entries_checked': checked, 'collisions': 0,
            'scope': 'relocation plan consistency only; no installation/migration performed'}


def demo_generated_reference():
    convert_file(env, 'base_industry_data', 'demo/res_users.xml', {}, mode='init')
    partner = env.ref('base_industry_data.res_users_7_res_partner', raise_if_not_found=False)
    assert partner, 'Expected generated partner XML ID was not created'
    convert_file(env, 'base_industry_data', 'data/res_partner_category.xml', {}, mode='init')
    convert_file(env, 'base_industry_data', 'demo/res_partner.xml', {}, mode='init')
    convert_file(env, 'base_industry_data', 'demo/res_partner_category.xml', {}, mode='init')
    return {'generated_xmlid_verified': 'base_industry_data.res_users_7_res_partner',
            'demo_category_file_loaded': True}


def community_user_menu_access():
    groups = [env.ref(xmlid).id for xmlid in (
        'base.group_user', 'sales_team.group_sale_salesman', 'purchase.group_purchase_user',
        'stock.group_stock_user', 'mrp.group_mrp_user', 'account.group_account_invoice')]
    user = env['res.users'].create({'name': 'AUDIT Business user',
        'login': 'audit-business-user@example.invalid', 'group_ids': [(6, 0, groups)],
        'company_id': env.company.id, 'company_ids': [(6, 0, env.company.ids)]})
    menu_model = env['ir.ui.menu'].with_user(user)
    visible = menu_model._visible_menu_ids()
    expected = ['sale.sale_menu_root', 'purchase.menu_purchase_root', 'stock.menu_stock_root',
                'mrp.menu_mrp_root', 'account.menu_finance']
    for xmlid in expected:
        assert env.ref(xmlid).id in visible, f'Menu hidden from business user: {xmlid}'
    for model in ('sale.order', 'purchase.order', 'stock.picking', 'mrp.production', 'account.move'):
        env[model].with_user(user).check_access('read')
    return {'visible_menu_xmlids': expected,
            'scope': 'non-admin menu visibility and model read access; no full ACL workflow test'}


def view_inheritance_structure():
    checked = []
    for (module, relative), tree in parsed.items():
        for record in tree.iter('record'):
            if record.get('model') != 'ir.ui.view':
                continue
            parent = record.find("field[@name='inherit_id']")
            arch = record.find("field[@name='arch']")
            if parent is None or arch is None:
                continue
            xmlid = parent.get('ref')
            view = env.ref(xmlid, raise_if_not_found=False)
            assert view, f'Missing parent: {xmlid}'
            base = deepcopy(view._get_combined_arch())
            wrapper = etree.Element('data')
            for child in arch:
                wrapper.append(etree.fromstring(ET.tostring(child)))
            apply_inheritance_specs(base, wrapper)
            checked.append({'id': f"{module}.{record.get('id')}", 'parent': xmlid})
    return {'checked': checked,
            'scope': 'XPath inheritance structure only; field validation and rendering not covered'}


def linked_food_workflow():
    company = env.company
    revenue = env['account.account'].create({
        'name': 'AUDIT chain income', 'code': 'AUDITE2REV', 'account_type': 'income',
        'company_ids': [(6, 0, company.ids)],
    })
    receivable = env['account.account'].create({
        'name': 'AUDIT chain receivable', 'code': 'AUDITE2REC',
        'account_type': 'asset_receivable', 'reconcile': True,
        'company_ids': [(6, 0, company.ids)],
    })
    customer = env['res.partner'].create({'name': 'AUDIT Chain customer',
        'property_account_receivable_id': receivable.id})
    supplier = env['res.partner'].create({'name': 'AUDIT Chain supplier'})
    item = product('tracked food chain', tracking='lot', use_expiration_date=True,
        expiration_time=30, invoice_policy='delivery', property_account_income_id=revenue.id)
    purchase = env['purchase.order'].create({'partner_id': supplier.id,
        'order_line': [(0, 0, {'product_id': item.id, 'product_qty': 5,
            'price_unit': 5, 'date_planned': fields.Datetime.now()})]})
    purchase.button_confirm()
    receipt = purchase.picking_ids
    assert len(receipt) == 1
    lot = env['stock.lot'].create({'name': 'AUDIT-FOOD-CHAIN', 'product_id': item.id,
                                  'company_id': company.id})
    for move in receipt.move_ids:
        move.move_line_ids.unlink()
        env['stock.move.line'].create({'move_id': move.id, 'picking_id': receipt.id,
            'product_id': item.id, 'product_uom_id': move.product_uom.id, 'quantity': 5,
            'location_id': move.location_id.id, 'location_dest_id': move.location_dest_id.id,
            'lot_id': lot.id})
        move.picked = True
    receipt.with_context(skip_backorder=True).button_validate()
    assert receipt.state == 'done'
    sale = env['sale.order'].create({'partner_id': customer.id,
        'order_line': [(0, 0, {'product_id': item.id, 'product_uom_qty': 2, 'price_unit': 12})]})
    sale.action_confirm()
    deliveries = sale.picking_ids.filtered(lambda p: p.state != 'cancel')
    for delivery in deliveries:
        validate_picking(delivery)
    delivered_lots = deliveries.move_line_ids.lot_id
    assert lot in delivered_lots
    invoice = sale._create_invoices()
    assert len(invoice) == 1
    invoice.invoice_date = fields.Date.today()
    invoice.action_post()
    assert invoice.state == 'posted' and invoice.amount_untaxed == 24
    assert sale.order_line.qty_invoiced == 2
    warehouse = sale.warehouse_id
    quants = env['stock.quant'].search([('product_id', '=', item.id), ('lot_id', '=', lot.id),
                                       ('location_id', '=', warehouse.lot_stock_id.id)])
    remaining = sum(quants.mapped('quantity'))
    assert remaining == 3
    return {'purchase': purchase.state, 'receipt': receipt.state,
        'same_lot_received_and_delivered': True, 'lot_expiration': str(lot.expiration_date),
        'sale': sale.state, 'delivery_states': deliveries.mapped('state'),
        'invoice': invoice.state, 'invoice_untaxed': invoice.amount_untaxed,
        'remaining_stock': remaining, 'uses_synthetic_accounts': True}


test('original_module_installation_expected_to_be_blocked', source_install_blocked)
test('relocation_plan_preserves_manifest_order', relocation_integrity)
test('community_sale_and_delivery', sale_delivery)
test('community_purchase_and_receipt', purchase_receipt)
test('community_lot_and_expiration', lot_expiry)
test('community_manufacturing', manufacturing)
test('community_invoice_posting', invoice_posting)
test('demo_user_partner_reference_generated_on_import', demo_generated_reference)
test('source_inherited_view_xpath_structure', view_inheritance_structure)
test('community_food_purchase_to_sale_invoice_same_lot', linked_food_workflow)
test('community_non_admin_business_menu_access', community_user_menu_access)

declared_models = {model['fields']['model'] for data in report['modules'].values()
                   for model in data['custom_models']}
declared_fields = set()
for module, data in report['modules'].items():
    local_models = {item['id']: item['fields']['model'] for item in data['custom_models']}
    for item in data['custom_fields']:
        reference = item['fields']['model_id']
        resolved = env.ref(reference, raise_if_not_found=False) if '.' in reference else None
        model_name = resolved.model if resolved else local_models.get(reference)
        declared_fields.add((model_name, item['fields']['name']))
    for item in data['missing_models']:
        item['classification'] = ('declared_by_source_module' if item['model'] in declared_models
                                  else 'model_not_in_installed_registry')
    for item in data['missing_fields']:
        item['classification'] = ('declared_by_source_module' if (item['model'], item['field']) in declared_fields
                                  else 'field_not_in_installed_registry')

if any(item['name'] == 'demo_user_partner_reference_generated_on_import' and item['status'] == 'passed'
       for item in report['tests']):
    base_data = report['modules']['base_industry_data']
    base_data['generated_reference_verified'] = 'base_industry_data.res_users_7_res_partner'
    base_data['unresolved_references'] = [item for item in base_data['unresolved_references']
        if item['xmlid'] != 'base_industry_data.res_users_7_res_partner']

env.cr.rollback()
report['rollback_verification'] = {
    'audit_products_remaining': env['product.product'].search_count([('name', 'like', 'AUDIT %')]),
    'audit_partners_remaining': env['res.partner'].search_count([('name', 'like', 'AUDIT %')]),
    'audit_journals_remaining': env['account.journal'].search_count([('code', '=', 'AUDT1')]),
}
output = Path('/tmp/food_distribution_audit_results.json')
output.write_text(json.dumps(report, indent=2, ensure_ascii=False, default=str), encoding='utf-8')
print('AUDIT_RESULTS=' + str(output), flush=True)
