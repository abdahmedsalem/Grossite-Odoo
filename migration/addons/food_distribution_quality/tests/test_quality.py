from odoo.tests import TransactionCase, tagged
from odoo.exceptions import UserError


@tagged('post_install', '-at_install')
class TestFoodQuality(TransactionCase):
    def _production(self):
        item = self.env['product.product'].create({'name': 'QC Test Food', 'type': 'consu', 'is_storable': True})
        bom = self.env['mrp.bom'].create({'product_tmpl_id': item.product_tmpl_id.id, 'product_qty': 1})
        production = self.env['mrp.production'].create({'product_id': item.id, 'product_qty': 1, 'bom_id': bom.id})
        test = self.env['qc.test'].create({'name': 'QC pH', 'test_lines': [(0, 0, {
            'name': 'pH', 'type': 'quantitative', 'min_value': 3.6, 'max_value': 4,
            'uom_id': self.env.ref('uom.product_uom_unit').id})]})
        point = self.env['food.quality.point'].create({'name': 'QC pH Point', 'test_id': test.id,
            'product_ids': [(6, 0, item.ids)]})
        return production, point

    def test_generation_idempotent_and_blocking(self):
        production, point = self._production()
        production.action_confirm()
        production._create_food_inspections()
        self.assertEqual(len(production.food_inspection_ids), 1)
        check = production.food_inspection_ids
        self.assertFalse(check.success)
        with self.assertRaises(UserError):
            production.button_mark_done()
        check.inspection_lines.quantitative_value = 3.8
        check.action_confirm()
        self.assertEqual(check.state, 'success')
        production.qty_producing = 1
        production.button_mark_done()
        self.assertEqual(production.state, 'done')

    def test_failed_measurement_blocks_completion(self):
        production, point = self._production()
        production.action_confirm()
        check = production.food_inspection_ids
        check.inspection_lines.quantitative_value = 6
        check.action_confirm()
        self.assertEqual(check.state, 'waiting')
        with self.assertRaises(UserError):
            production._check_food_quality()

    def test_other_company_point_not_used(self):
        production, point = self._production()
        other = self.env['res.company'].create({'name': 'QC Other Company'})
        point.test_id.company_id = other
        point.company_id = other
        production.action_confirm()
        self.assertFalse(production.food_inspection_ids)

    def test_ordinary_mrp_without_points_unchanged(self):
        production, point = self._production()
        point.active = False
        production.action_confirm()
        self.assertFalse(production.food_inspection_ids)
        production.qty_producing = 1
        production.button_mark_done()
        self.assertEqual(production.state, 'done')

    def test_manufacturing_user_can_record_quality(self):
        production, point = self._production()
        user = self.env['res.users'].with_context(no_reset_password=True).create({
            'name': 'Food MRP Operator', 'login': 'food-mrp-operator@example.invalid',
            'company_id': self.env.company.id, 'company_ids': [(6, 0, self.env.company.ids)],
            'group_ids': [(6, 0, [self.env.ref('mrp.group_mrp_user').id])]})
        production.with_user(user).action_confirm()
        check = production.with_user(user).food_inspection_ids
        self.assertEqual(len(check), 1)
        check.inspection_lines.quantitative_value = 3.8
        check.action_confirm()
        self.assertEqual(check.state, 'success')

    def test_qualitative_answer_required(self):
        production, point = self._production()
        qualitative = self.env['qc.test'].create({'name': 'Verify ingredient lot', 'test_lines': [(0, 0, {
            'name': 'Ingredient lot checked', 'type': 'qualitative', 'ql_values': [
                (0, 0, {'name': 'Verified', 'ok': True}),
                (0, 0, {'name': 'Not verified', 'ok': False})]})]})
        point.test_id = qualitative
        production.action_confirm()
        check = production.food_inspection_ids
        with self.assertRaises(UserError):
            check.action_confirm()
        check.inspection_lines.qualitative_value = qualitative.test_lines.ql_values.filtered('ok')
        check.action_confirm()
        self.assertEqual(check.state, 'success')

    def test_label_generation_required_when_enabled(self):
        production, point = self._production()
        self.env.company.x_module_food_drinks_labels = True
        production.product_id.tracking = 'lot'
        point.label_step = True
        production.action_confirm()
        check = production.food_inspection_ids
        check.inspection_lines.quantitative_value = 3.8
        check.action_confirm()
        with self.assertRaises(UserError):
            production._check_food_quality()
        lot = self.env['stock.lot'].create({'name': 'Food QC Label Lot', 'product_id': production.product_id.id,
                                          'company_id': self.env.company.id})
        production.lot_producing_ids = lot
        action = check.action_print_food_label()
        self.assertTrue(check.food_label_printed)
        self.assertEqual(action['report_name'], 'food_distribution.report_food_lot_label')
        production._check_food_quality()
