# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class StockInventory(models.Model):
    _inherit = "stock.inventory"
    
    def _cron_generate_inventories(self):
        Location = self.env['stock.location']
        Inventory = self.env['stock.inventory']
        kiosk_ids = Location.search([('is_kiosk', '=', True)])
        inventory_to_cancel = Inventory.search([('state', '=', 'confirm')])
        if inventory_to_cancel:
            # set all inventories in state confirm to draft
            inventory_to_cancel.action_cancel_draft()

        for kiosk_id in kiosk_ids:
            vals = {'name': _('Inventory %s %s') % (kiosk_id.name, fields.Datetime.now()),
                    'location_id': kiosk_id.id,
                    'filter': 'none'}
            inventory_id = Inventory.create(vals)
            inventory_id.prepare_inventory()
            for line in inventory_id.line_ids:
                if line.theoretical_qty < 0.0:
                    line.product_qty = 0.0
                else:
                    line.product_qty = line.theoretical_qty

            inventory_id.action_done()
            

class ContractorLine(models.Model):
    _name = "contractor.line"
    _order = "date_start desc"
    
    partner_id = fields.Many2one('res.partner', string='Partner', required=True)
    status = fields.Boolean(string='Active')
    date_start = fields.Datetime('Date start', default=fields.Datetime.now)
    date_end = fields.Datetime('Date end')
    kiosk_id = fields.Many2one('stock.location', string='Kiosk')
    
    @api.model
    def create(self, values):
        res = super(ContractorLine, self).create(values)
        if values.get('status') and values.get('kiosk_id'):
            contractor_lines = self.search([('id', '!=', res.id), ('kiosk_id', '=', values.get('kiosk_id')), ('status', '=', True)])
            for line in contractor_lines:
                line.status = False
        return res


class StockLocation(models.Model):
    _inherit = "stock.location"

    is_kiosk = fields.Boolean(string='Is a kiosk ?')
    billing_table_id = fields.Many2one('billing.table', string='Billing table')
    contractor_ids = fields.One2many('contractor.line', 'kiosk_id', string='Contractors')