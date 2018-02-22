# -*- coding: utf-8 -*-

from odoo import models, fields, api


class AccountInvoice(models.Model):
    _inherit = "account.invoice"
    
    
    @api.model
    def _default_account_type(self):
        if self._context.get('invoice_type', False):
            return self._context.get('invoice_type', False)
    
    kiosk_id = fields.Many2one('stock.location', string='Kiosk *')
    date_start = fields.Datetime(string='Start date')
    date_end = fields.Datetime(string='End date')
    invoice_type = fields.Selection([('rental', 'Rental'), ('sale', 'Sale'), ('loss', 'Loss')], string="Type invoice", default=_default_account_type)