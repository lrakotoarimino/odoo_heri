# -*- coding: utf-8 -*-

from odoo import fields, models, api


class ResPartner(models.Model):
    _inherit = 'res.partner'
    
    kiosk_id = fields.Many2one('stock.location', string='Kiosk')