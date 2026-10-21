"""Enable native features used by the supplied food workflows, without demo data."""
import json
from pathlib import Path

assert env.cr.dbname == 'food_distribution' or env.cr.dbname.startswith('food_distribution_migration_')
settings_model = env['res.config.settings']
requested = ['group_uom', 'group_sale_order_template', 'group_discount_per_so_line',
    'group_stock_multi_locations', 'group_mrp_routings', 'group_mrp_workorder_dependencies',
    'group_unlocked_by_default', 'group_product_pricelist',
    'group_stock_production_lot', 'group_expiry_date']
values = {name: True for name in requested if name in settings_model._fields}
settings = settings_model.create(values)
settings.execute()
env.company.x_module_food_drinks_labels = True
env['ir.config_parameter'].sudo().set_param('report.url', 'http://127.0.0.1:8069')
env.cr.commit()
result = {'database': env.cr.dbname, 'native_settings_enabled': sorted(values),
          'food_labels_enabled': True, 'demo_data_loaded': False}
Path('/tmp/migration-configured.json').write_text(json.dumps(result, indent=2))
print(json.dumps(result), flush=True)
