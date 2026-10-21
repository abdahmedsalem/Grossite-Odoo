from odoo import api, fields, models


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    x_label_note = fields.Text('Label Note')
    x_is_allergen = fields.Boolean('Is Allergen')
    x_ingredient_ids = fields.One2many('x_product_template_ingredients', 'x_product_template_id', string='Ingredients')
    x_nutritional_fact_ids = fields.One2many('x_product_template_nutritional_fact', 'x_product_template_id', string='Nutritional Facts')
    x_food_labels_enabled = fields.Boolean(compute='_compute_food_labels_enabled')

    @api.depends_context('company')
    def _compute_food_labels_enabled(self):
        for product in self:
            product.x_food_labels_enabled = self.env.company.x_module_food_drinks_labels
