from odoo import api, fields, models, _
from odoo.exceptions import UserError


class FoodQualityPoint(models.Model):
    _name = 'food.quality.point'
    _description = 'Food manufacturing quality point'
    _check_company_auto = True

    name = fields.Char(required=True)
    active = fields.Boolean(default=True)
    test_id = fields.Many2one('qc.test', required=True, check_company=True)
    product_ids = fields.Many2many('product.product', string='Products', required=True)
    operation_id = fields.Many2one('mrp.routing.workcenter', string='Operation', check_company=True)
    component_id = fields.Many2one('product.product', string='Component to verify')
    label_step = fields.Boolean('Require food label generation')
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)


class QcInspection(models.Model):
    _inherit = 'qc.inspection'

    food_production_id = fields.Many2one('mrp.production', index=True, ondelete='cascade', check_company=True)
    food_workorder_id = fields.Many2one('mrp.workorder', index=True, ondelete='set null', check_company=True)
    food_point_id = fields.Many2one('food.quality.point', ondelete='restrict', check_company=True)
    food_label_printed = fields.Boolean(readonly=True, copy=False)
    _food_point_unique = models.Constraint(
        'UNIQUE(food_production_id, food_point_id)', 'A quality point can only be generated once per manufacturing order.')

    def action_print_food_label(self):
        self.ensure_one()
        if not self.food_point_id.label_step:
            raise UserError(_('This inspection is not a food label step.'))
        lots = self.food_production_id.lot_producing_ids
        if not lots:
            raise UserError(_('Assign the production lot before generating its food label.'))
        self.food_label_printed = True
        # The label uses basic_layout, so a company document-layout wizard is
        # unnecessary and must not be counted as a generated label request.
        return self.env.ref('food_distribution.action_report_food_lot_label').report_action(lots, config=False)


class MrpProduction(models.Model):
    _inherit = 'mrp.production'

    food_inspection_ids = fields.One2many('qc.inspection', 'food_production_id', string='Food quality inspections')

    def _create_food_inspections(self):
        for production in self:
            points = self.env['food.quality.point'].search([
                ('product_ids', 'in', production.product_id.ids),
                ('company_id', 'in', [False, production.company_id.id]),
            ])
            for point in points:
                if point.label_step and not production.company_id.x_module_food_drinks_labels:
                    continue
                if point.operation_id and point.operation_id not in production.bom_id.operation_ids:
                    continue
                if point in production.food_inspection_ids.food_point_id:
                    continue
                inspection_model = self.env['qc.inspection'].with_company(production.company_id)
                inspection_model.create({
                    'food_production_id': production.id, 'food_point_id': point.id,
                    'food_workorder_id': production.workorder_ids.filtered(
                        lambda work: work.operation_id == point.operation_id)[:1].id,
                    'object_id': 'product.product,%s' % production.product_id.id,
                    'company_id': production.company_id.id, 'test': point.test_id.id,
                    'qty': production.product_qty, 'auto_generated': True, 'state': 'ready',
                    'inspection_lines': inspection_model._prepare_inspection_lines(point.test_id),
                })

    def action_confirm(self):
        result = super().action_confirm()
        self._create_food_inspections()
        return result

    def _check_food_quality(self):
        for production in self:
            blocked = production.food_inspection_ids.filtered(
                lambda check: check.state != 'success' or
                (check.food_point_id.label_step and not check.food_label_printed))
            if blocked:
                raise UserError(_('Complete the food quality inspections before finishing production: %s',
                                  ', '.join(blocked.mapped('name'))))

    def button_mark_done(self):
        self._create_food_inspections()
        self._check_food_quality()
        return super().button_mark_done()


class MrpWorkorder(models.Model):
    _inherit = 'mrp.workorder'

    food_inspection_ids = fields.One2many('qc.inspection', 'food_workorder_id', string='Food quality inspections')

    def button_finish(self):
        for workorder in self:
            if workorder.food_inspection_ids.filtered(lambda check: check.state != 'success'):
                raise UserError(_('Complete the food quality inspections for this operation first.'))
        return super().button_finish()
