# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class StockInventory(models.Model):
    _inherit = "stock.inventory"
    
    def _cron_generate_inventories(self):
        print 'Inventory is RUNNING!!!!!!!!'
        Location = self.env['stock.location']
        Inventory = self.env['stock.inventory']
        kiosk_ids = Location.search([('is_kiosk', '=', True)])
        for kiosk_id in kiosk_ids:
            vals = {'name': _('Inventory %s %s') % (kiosk_id.name, fields.Datetime.now()),
                    'location_id': kiosk_id.id,
                    'filter': 'none'}
            inventory_id = Inventory.create(vals)
            inventory_id.prepare_inventory()
            # inventory_id.action_done()
            

class StockLocation(models.Model):
    _inherit = "stock.location"
    
    def _default_billing_table_id(self):
        return self.env.ref('sale_advanced_heri.billing_table_1').id
        
    billing_table_id = fields.Many2one('billing.table', string='Billing table', default=_default_billing_table_id)