# -*- coding: utf-8 -*-

from odoo import models, fields


class AccountInvoice(models.Model):
    _inherit = "account.invoice"

    kiosk_id = fields.Many2one('stock.location', string='Kiosk *')
    date_start = fields.Datetime(string='Start date')
    date_end = fields.Datetime(string='End date')
    invoice_type = fields.Selection([('rental', 'Rental'), ('sale', 'Sale'), ('loss', 'Loss')], string="Type invoice")