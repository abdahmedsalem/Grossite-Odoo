from odoo.tests import TransactionCase, tagged
from odoo.exceptions import UserError, ValidationError


@tagged('post_install', '-at_install')
class TestFoodForecast(TransactionCase):
    def _forecast(self):
        item = self.env['product.product'].create({'name': 'Forecast Test Food', 'type': 'consu', 'is_storable': True})
        bom = self.env['mrp.bom'].create({'product_tmpl_id': item.product_tmpl_id.id, 'product_qty': 1})
        return self.env['food.production.forecast'].create({'product_id': item.id, 'bom_id': bom.id, 'quantity': 4})

    def test_native_manufacturing_and_no_duplicate(self):
        forecast = self._forecast()
        forecast.action_create_production()
        first = forecast.production_id
        self.assertEqual(first.product_qty, 4)
        self.assertEqual(first.state, 'confirmed')
        forecast.action_create_production()
        self.assertEqual(forecast.production_id, first)
        with self.assertRaises(UserError):
            forecast.quantity = 5

    def test_invalid_quantity_and_dates(self):
        forecast = self._forecast()
        with self.assertRaises(ValidationError), self.cr.savepoint():
            forecast.quantity = 0

    def test_mismatched_bom_rejected(self):
        forecast = self._forecast()
        other = self.env['product.product'].create({'name': 'Other Forecast Food'})
        with self.assertRaises(ValidationError), self.cr.savepoint():
            forecast.product_id = other
