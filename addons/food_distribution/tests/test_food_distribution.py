from odoo.tests import TransactionCase, tagged
from odoo.exceptions import AccessError, UserError


@tagged('post_install', '-at_install')
class TestFoodDistribution(TransactionCase):
    def test_related_fields_and_archiving(self):
        fact = self.env['x_nutritional_facts'].create({'x_name': 'Test Energy', 'x_sequence': 3,
            'x_unit_id': self.env.ref('uom.product_uom_gram').id})
        self.assertTrue(fact.x_active)
        ingredient = self.env['product.template'].create({'name': 'Test Egg', 'x_is_allergen': True})
        product = self.env['product.template'].create({'name': 'Test Food',
            'x_ingredient_ids': [(0, 0, {'x_ingredient_id': ingredient.id, 'x_share': 6})],
            'x_nutritional_fact_ids': [(0, 0, {'x_nutritional_fact_id': fact.id, 'x_per_100g': 10})]})
        self.assertTrue(product.x_ingredient_ids.x_is_allergen)
        self.assertEqual(product.x_nutritional_fact_ids.x_sequence, 3)
        ingredient.x_is_allergen = False
        fact.x_sequence = 8
        self.assertFalse(product.x_ingredient_ids.x_is_allergen)
        self.assertEqual(product.x_nutritional_fact_ids.x_sequence, 8)
        fact.x_active = False
        self.assertNotIn(fact, self.env['x_nutritional_facts'].search([('id', '=', fact.id)]))
        self.assertIn(fact, self.env['x_nutritional_facts'].with_context(active_test=False).search([('id', '=', fact.id)]))

    def test_internal_user_rights(self):
        user = self.env['res.users'].with_context(no_reset_password=True).create({
            'name': 'Food Test User', 'login': 'food-test-user@example.invalid',
            'group_ids': [(6, 0, [self.env.ref('base.group_user').id])]})
        fact = self.env['x_nutritional_facts'].with_user(user).create({'x_name': 'Test Protein'})
        fact.write({'x_name': 'Test Protein updated'})
        with self.assertRaises(AccessError):
            fact.unlink()

    def test_legacy_xmlids_and_field_types(self):
        self.assertEqual(self.env.ref('food_distribution.field_product_template_label_note').name, 'x_label_note')
        self.assertEqual(self.env['x_product_template_ingredients']._fields['x_share'].type, 'integer')
        self.assertFalse(self.env['x_product_template_nutritional_fact']._fields['x_unit_id'].store)
        self.assertEqual(self.env['product.template']._fields['x_ingredient_ids'].inverse_name, 'x_product_template_id')

    def test_company_setting_does_not_mutate_global_report(self):
        other = self.env['res.company'].create({'name': 'Food Other Company'})
        original = self.env.ref('stock.action_report_lot_label').paperformat_id
        self.env.company.x_module_food_drinks_labels = True
        self.assertFalse(other.x_module_food_drinks_labels)
        self.assertEqual(self.env.ref('stock.action_report_lot_label').paperformat_id, original)

    def test_bom_label_uses_food_data_without_creating_lot(self):
        self.env.company.x_module_food_drinks_labels = True
        product = self.env['product.product'].create({'name': 'BOM Label Test Food', 'x_label_note': 'Keep chilled'})
        bom = self.env['mrp.bom'].create({'product_tmpl_id': product.product_tmpl_id.id})
        count = self.env['stock.lot'].search_count([('product_id', '=', product.id)])
        html, _ = self.env['ir.actions.report']._render_qweb_html('food_distribution.mrp_bom_product_label_action_report', bom.ids)
        self.assertIn(b'Keep chilled', html)
        self.assertEqual(self.env['stock.lot'].search_count([('product_id', '=', product.id)]), count)

    def test_disabled_food_labels_keep_standard_report(self):
        self.env.company.x_module_food_drinks_labels = False
        item = self.env['product.product'].create({'name': 'Standard Label Test Food'})
        lot = self.env['stock.lot'].create({'name': 'StandardLabel001', 'product_id': item.id, 'company_id': self.env.company.id})
        with self.assertRaises(UserError):
            self.env['ir.actions.report']._render_qweb_html('food_distribution.action_report_food_lot_label', lot.ids)
        html, _ = self.env['ir.actions.report']._render_qweb_html('stock.action_report_lot_label', lot.ids)
        self.assertIn(b'StandardLabel001', html)

    def test_legacy_sequence_write_and_duplication(self):
        fact = self.env['x_nutritional_facts'].create({'x_name': 'Legacy Sequence Fact', 'x_sequence': 4})
        ingredient = self.env['product.template'].create({'name': 'Legacy Copy Ingredient'})
        product = self.env['product.template'].create({'name': 'Legacy Copy Product', 'x_label_note': 'Original note',
            'x_ingredient_ids': [(0, 0, {'x_ingredient_id': ingredient.id, 'x_share': 5})],
            'x_nutritional_fact_ids': [(0, 0, {'x_nutritional_fact_id': fact.id, 'x_per_100g': 12})]})
        product.x_nutritional_fact_ids.write({'x_sequence': 19})
        self.assertEqual(fact.x_sequence, 19)
        self.assertEqual(product.x_nutritional_fact_ids.food_sort_sequence, 19)
        duplicate = product.copy({'name': 'Legacy Copy Result'})
        self.assertEqual(duplicate.x_label_note, 'Original note')
        self.assertFalse(duplicate.x_ingredient_ids)
        self.assertFalse(duplicate.x_nutritional_fact_ids)

    def test_legacy_company_setting_is_stored_and_related(self):
        self.env.company.x_module_food_drinks_labels = False
        settings = self.env['res.config.settings'].create({'company_id': self.env.company.id})
        settings.x_module_food_drinks_labels = True
        self.assertTrue(self.env.company.x_module_food_drinks_labels)
        settings.flush_recordset(['x_module_food_drinks_labels'])
        self.cr.execute('SELECT x_module_food_drinks_labels FROM res_config_settings WHERE id=%s', [settings.id])
        self.assertTrue(self.cr.fetchone()[0])
