# -*- coding: utf-8 -*-

from odoo import models, fields, api, _

from odoo.exceptions import UserError

import odoo.addons.decimal_precision as dp

# mapping invoice type to journal type
TYPE2JOURNAL = {
    'out_invoice': 'sale',
    'in_invoice': 'purchase',
    'out_refund': 'sale',
    'in_refund': 'purchase',
}

INVOICETYPE2CODE = {
    'rental': 'RED',
    'sale': 'VTE',
    'loss': 'PRT',
}


class AccountInvoice(models.Model):
    _inherit = "account.invoice"
    
    @api.model
    def _default_account_type(self):
        if self._context.get('invoice_type', False):
            return self._context.get('invoice_type', False)
        
    @api.model
    def _default_journal(self):
        if self._context.get('default_journal_id', False):
            return self.env['account.journal'].browse(self._context.get('default_journal_id'))
        inv_type = self._context.get('type', 'out_invoice')
        inv_types = inv_type if isinstance(inv_type, list) else [inv_type]
        company_id = self._context.get('company_id', self.env.user.company_id.id)
        domain = [
            ('type', 'in', filter(None, map(TYPE2JOURNAL.get, inv_types))),
            ('company_id', '=', company_id),
        ]
        
        # redefinition
        if self._context.get('invoice_type', False):
            invoice_type = self._context.get('invoice_type')
            if invoice_type in ('rental', 'sale', 'loss'):
                domain.append(('code', '=', INVOICETYPE2CODE[invoice_type]),)
                if not self.env['account.journal'].search(domain, limit=1):
                    raise UserError(_("Configuration error!\nCould not find account journal with code %s") % INVOICETYPE2CODE[invoice_type])
        return self.env['account.journal'].search(domain, limit=1)
    
    @api.onchange('kiosk_id')
    def _onchange_kiosk_id(self):
        if not self.kiosk_id:
            self.partner_id = False
            return
          
        partner_id = self.env['res.partner'].search([('kiosk_id', '=', self.kiosk_id.id)], limit=1)
        if partner_id:
            self.partner_id = partner_id.id
        else:
            self.partner_id = False
      
    @api.onchange('partner_id', 'company_id')
    def _onchange_partner_id(self):
        res = super(AccountInvoice, self)._onchange_partner_id()
        if self.partner_id and self.partner_id.kiosk_id:
            self.kiosk_id = self.partner_id.kiosk_id.id
        return res
    
    @api.onchange('date_start', 'date_end')
    def _onchange_billing_date(self):
        if self.date_start and self.date_end:
            if self.date_start >= self.date_end:
                return {
                'warning': {'title': _('Error!'), 'message': _('The start date must be strictly less than the end date'), },
                'value': {'date_start': False, 'date_end': False, }
                }
                 
    journal_id = fields.Many2one('account.journal', string='Journal',
        required=True, readonly=True, states={'draft': [('readonly', False)]},
        default=_default_journal,
        domain="[('type', 'in', {'out_invoice': ['sale'], 'out_refund': ['sale'], 'in_refund': ['purchase'], 'in_invoice': ['purchase']}.get(type, [])), ('company_id', '=', company_id)]")
    kiosk_id = fields.Many2one('stock.location', string='Kiosk *')
    date_start = fields.Datetime(string='Start date')
    date_end = fields.Datetime(string='End date')
    invoice_type = fields.Selection([('rental', 'Rental'), ('sale', 'Sale'), ('loss', 'Loss')], string="Type invoice", default=_default_account_type)
    
    kiosk_id = fields.Many2one('stock.location', string='Kiosk *')
    date_start = fields.Date(string='Billing start date')
    date_end = fields.Date(string='Billing end date')
    
    def get_invoice_line(self):
        print 'Error'
    

class AccountInvoiceLine(models.Model):
    _inherit = "account.invoice.line"
    
    @api.depends('price_unit', 'discount', 'invoice_line_tax_ids', 'quantity',
    'product_id', 'invoice_id.partner_id', 'invoice_id.currency_id', 'invoice_id.company_id',
    'invoice_id.date_invoice', 'number_days')
    def _compute_price(self):
        currency = self.invoice_id and self.invoice_id.currency_id or None
        price = self.number_days * self.price_unit * (1 - (self.discount or 0.0) / 100.0)
        taxes = False
        if self.invoice_line_tax_ids:
            taxes = self.invoice_line_tax_ids.compute_all(price, currency, self.quantity, product=self.product_id, partner=self.invoice_id.partner_id)
        self.price_subtotal = price_subtotal_signed = taxes['total_excluded'] if taxes else self.quantity * price
        if self.invoice_id.currency_id and self.invoice_id.company_id and self.invoice_id.currency_id != self.invoice_id.company_id.currency_id:
            price_subtotal_signed = self.invoice_id.currency_id.with_context(date=self.invoice_id.date_invoice).compute(price_subtotal_signed, self.invoice_id.company_id.currency_id)
        sign = self.invoice_id.type in ['in_refund', 'out_refund'] and -1 or 1
        self.price_subtotal_signed = price_subtotal_signed * sign
    
    date = fields.Date(string='Date', default=fields.Date.context_today)
    number_days = fields.Float(string='Days', digits=dp.get_precision('Product Unit of Measure'), default=1.0)


class AccountJournal(models.Model):
        _inherit = "account.journal"
        _sql_constraints = [('code_uniq', 'unique(code)', "A code must be unique !")]