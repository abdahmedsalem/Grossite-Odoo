from odoo import api, models, _
from odoo.exceptions import UserError


class FoodLotLabelReport(models.AbstractModel):
    _name = 'report.food_distribution.report_food_lot_label'
    _description = 'Food and drinks lot label'

    @api.model
    def _get_report_values(self, docids, data=None):
        lots = self.env['stock.lot'].browse(docids).exists()
        lots.check_access('read')
        companies = lots.company_id or self.env.company
        if any(not company.x_module_food_drinks_labels for company in companies):
            raise UserError(_('Enable Food & Drinks Labels in the corresponding company settings before printing.'))
        return {'doc_ids': lots.ids, 'doc_model': 'stock.lot', 'docs': lots}


class FoodBomLabelReport(models.AbstractModel):
    _name = 'report.food_distribution.report_bom_food_label'
    _description = 'Food product label from a bill of materials'

    @api.model
    def _get_report_values(self, docids, data=None):
        boms = self.env['mrp.bom'].browse(docids).exists()
        boms.check_access('read')
        labels = self.env['stock.lot']
        for bom in boms:
            company = bom.company_id or self.env.company
            if not company.x_module_food_drinks_labels:
                raise UserError(_('Enable Food & Drinks Labels before printing.'))
            # A virtual record reuses the lot label layout without creating stock
            # or inventing a batch number/expiration date before production.
            labels += self.env['stock.lot'].new({
                'product_id': (bom.product_id or bom.product_tmpl_id.product_variant_id).id,
                'company_id': company.id, 'name': '', 'use_expiration_date': False,
                'expiration_date': False, 'use_date': False,
            })
        return {'doc_ids': boms.ids, 'doc_model': 'mrp.bom', 'docs': labels}
