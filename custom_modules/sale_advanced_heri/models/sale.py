# -*- coding: utf-8 -*-

from odoo import api, fields, models


class SaleOrder(models.Model):
    _inherit = "sale.order"
    
#     kiosk_id = fields.Many2one('stock.location', string='Kiosk *')
#     date_start = fields.Datetime(string='Billing start date')
#     date_end = fields.Datetime(string='Billing end date')
#     
#     @api.onchange('kiosk_id')
#     def onchange_kiosk_id(self):
#         if not self.kiosk_id:
#             self.partner_id = False
#             return
#          
#         partner_id = self.env['res.partner'].search([('kiosk_id', '=', self.kiosk_id.id)], limit=1)
#         if partner_id:
#             self.partner_id = partner_id.id
#         else:
#             self.partner_id = False
#      
#     @api.onchange('partner_id')
#     def onchange_partner_id(self):
#         super(SaleOrder, self).onchange_partner_id()
#         if self.partner_id and self.partner_id.kiosk_id:
#             self.kiosk_id = self.partner_id.kiosk_id.id
#     
#     def get_order_line(self):
#         print 'Error'