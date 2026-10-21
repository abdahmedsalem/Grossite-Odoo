from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class FoodProductionForecast(models.Model):
    _name = 'food.production.forecast'
    _description = 'Food production forecast'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _check_company_auto = True
    _order = 'date_start, id'
    _rec_name = 'product_id'

    product_id = fields.Many2one('product.product', required=True, check_company=True)
    product_tmpl_id = fields.Many2one(related='product_id.product_tmpl_id', readonly=True)
    company_id = fields.Many2one('res.company', required=True, default=lambda self: self.env.company)
    bom_id = fields.Many2one('mrp.bom', check_company=True)
    date_start = fields.Date(required=True, default=fields.Date.today)
    date_end = fields.Date(required=True, default=fields.Date.today)
    quantity = fields.Float(required=True, default=1, tracking=True)
    production_id = fields.Many2one('mrp.production', readonly=True, copy=False, check_company=True)
    state = fields.Selection([('draft', 'Forecast'), ('planned', 'Manufacturing Order Created')], default='draft', readonly=True, tracking=True)

    def write(self, values):
        if set(values) & {'quantity', 'product_id', 'bom_id', 'date_start', 'date_end', 'company_id'}:
            if self.filtered('production_id'):
                raise UserError(_('Edit the linked manufacturing order or create a new forecast after planning.'))
        return super().write(values)

    @api.constrains('quantity', 'date_start', 'date_end', 'bom_id', 'product_id')
    def _check_forecast(self):
        for forecast in self:
            if forecast.quantity <= 0 or forecast.date_end < forecast.date_start:
                raise ValidationError(_('Use a positive quantity and a valid date range.'))
            if forecast.bom_id and (forecast.bom_id.product_tmpl_id != forecast.product_id.product_tmpl_id or
                                     forecast.bom_id.product_id and forecast.bom_id.product_id != forecast.product_id):
                raise ValidationError(_('The bill of materials must match the forecast product.'))

    def action_create_production(self):
        for forecast in self:
            # Serialize concurrent button clicks; reuse native MRP for all stock
            # demands, operations, lot traceability and consumption.
            self.env.cr.execute('SELECT id FROM food_production_forecast WHERE id=%s FOR UPDATE', [forecast.id])
            forecast.invalidate_recordset(['production_id', 'state'])
            if forecast.production_id:
                continue
            bom = forecast.bom_id or self.env['mrp.bom']._bom_find(
                forecast.product_id, company_id=forecast.company_id.id).get(forecast.product_id)
            if not bom:
                raise UserError(_('Configure a bill of materials before planning production.'))
            if bom.type != 'normal':
                raise UserError(_('A production forecast requires a manufacturing bill of materials, not a kit.'))
            production = self.env['mrp.production'].with_company(forecast.company_id).create({
                'product_id': forecast.product_id.id, 'product_qty': forecast.quantity,
                'product_uom_id': forecast.product_id.uom_id.id, 'bom_id': bom.id,
                'company_id': forecast.company_id.id,
                'date_start': fields.Datetime.to_datetime(forecast.date_start),
                'date_deadline': fields.Datetime.to_datetime(forecast.date_end),
                'origin': 'Food Forecast %s' % forecast.id,
            })
            production.action_confirm()
            forecast.write({'production_id': production.id, 'state': 'planned'})
        if len(self) == 1:
            return {'type': 'ir.actions.act_window', 'res_model': 'mrp.production',
                    'res_id': self.production_id.id, 'view_mode': 'form'}
        return True
