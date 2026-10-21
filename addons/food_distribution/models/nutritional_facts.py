from odoo import fields, models


class NutritionalFacts(models.Model):
    _name = 'x_nutritional_facts'
    _description = 'Nutritional Facts'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'x_name'
    _active_name = 'x_active'
    _order = 'id'

    x_name = fields.Char('Description', required=True, translate=True, tracking=True)
    x_active = fields.Boolean('Active', default=True, tracking=True)
    x_sequence = fields.Integer('Sequence')
    x_parent = fields.Many2one('x_nutritional_facts', string='Parent')
    x_unit_id = fields.Many2one('uom.uom', string='Unit')


class ProductIngredients(models.Model):
    _name = 'x_product_template_ingredients'
    _description = 'Product Template Ingredients'
    _rec_name = None
    _order = 'id'

    x_product_template_id = fields.Many2one('product.template', string='Product', ondelete='set null')
    x_ingredient_id = fields.Many2one('product.template', string='Ingredient')
    x_is_allergen = fields.Boolean('Is Allergen', related='x_ingredient_id.x_is_allergen', readonly=True, store=False)
    x_sequence = fields.Integer('Sequence')
    x_share = fields.Integer('Proportion (%)')


class ProductNutritionalFacts(models.Model):
    _name = 'x_product_template_nutritional_fact'
    _description = 'Product Template Nutritional Fact'
    _rec_name = None
    _order = 'id'

    x_product_template_id = fields.Many2one('product.template', string='Product', ondelete='set null')
    x_nutritional_fact_id = fields.Many2one('x_nutritional_facts', string='Nutritional Fact')
    x_per_100g = fields.Float('Per 100g', required=True)
    x_unit_id = fields.Many2one('uom.uom', string='Unit', related='x_nutritional_fact_id.x_unit_id', readonly=True, store=False, ondelete='set null')
    x_sequence = fields.Integer('Sequence', related='x_nutritional_fact_id.x_sequence', store=False, readonly=False)
    food_sort_sequence = fields.Integer('Nutrition Sort Sequence', related='x_nutritional_fact_id.x_sequence', store=True, index=True)
