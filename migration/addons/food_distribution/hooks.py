from pathlib import Path
import ast


def field_aliases(env):
    mapping = ast.literal_eval((Path(__file__).parent / 'data/legacy_field_map.txt').read_text(encoding='utf-8'))
    env['ir.model.data']._update_xmlids([
        {'xml_id': 'food_distribution.' + old,
         'record': env.ref('food_distribution.field_' + model.replace('.', '_') + '__' + name),
         'noupdate': True}
        for old, model, name in mapping
    ])


def field_aliases_sql(cr):
    """Keep legacy field XML IDs across both install and module update.

    The old IDs pointed to ``ir.model.fields`` rows created by Studio/XML.
    During an update Odoo removes data records owned by the module before the
    post-init hook runs, so recreate the aliases directly from the stable
    field rows in SQL as part of the pre-init phase too.
    """
    mapping = ast.literal_eval((Path(__file__).parent / 'data/legacy_field_map.txt').read_text(encoding='utf-8'))
    for old, model, name in mapping:
        cr.execute("""
            INSERT INTO ir_model_data (module, name, model, res_id, noupdate)
            SELECT 'food_distribution', %s, 'ir.model.fields', f.id, TRUE
              FROM ir_model_fields f
             WHERE f.model=%s AND f.name=%s
            ON CONFLICT (module, name) DO UPDATE
                SET model=EXCLUDED.model, res_id=EXCLUDED.res_id, noupdate=TRUE
        """, [old, model, name])


def pre_init_hook(env):
    # Preserve existing tables and columns when previous XML/Studio fields exist.
    model_names = ['x_nutritional_facts', 'x_product_template_ingredients', 'x_product_template_nutritional_fact']
    env.cr.execute("UPDATE ir_model SET state='base' WHERE model IN %s AND state='manual'", [tuple(model_names)])
    mapping = ast.literal_eval((Path(__file__).parent / 'data/legacy_field_map.txt').read_text(encoding='utf-8'))
    for _old, model, name in mapping:
        env.cr.execute("UPDATE ir_model_fields SET state='base' WHERE model=%s AND name=%s AND state='manual'", [model, name])
    field_aliases_sql(env.cr)


def post_init_hook(env):
    field_aliases(env)
