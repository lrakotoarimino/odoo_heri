# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class StockSettings(models.TransientModel):
    _inherit = 'stock.config.settings'
    
    @api.multi
    def validate_all_inventories(self):
        self.ensure_one()
        all_inventory = self.env['stock.inventory'].search([('state', '!=', 'done')])
        
        for inv in all_inventory:
            inv.prepare_inventory()
            inv.action_done()