from odoo import api, fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    x_module_food_drinks_labels = fields.Boolean('Food & Drinks Labels')

    def write(self, values):
        result = super().write(values)
        if 'x_module_food_drinks_labels' in values:
            self.env.registry.clear_cache()
        return result


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    x_module_food_drinks_labels = fields.Boolean(
        'Food & Drinks Labels', related='company_id.x_module_food_drinks_labels', readonly=False, store=True)


class IrUiMenu(models.Model):
    _inherit = 'ir.ui.menu'

    @api.model
    def _visible_menu_ids(self, debug=False):
        visible = super()._visible_menu_ids(debug=debug)
        menu = self.env.ref('food_distribution.inventory_nutritional_facts_menu', raise_if_not_found=False)
        if menu and not self.env.company.x_module_food_drinks_labels:
            return visible - {menu.id}
        return visible
