# -*- coding: utf-8 -*-

from odoo import models, fields, api, _

from odoo.exceptions import UserError

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
        
    journal_id = fields.Many2one('account.journal', string='Journal',
        required=True, readonly=True, states={'draft': [('readonly', False)]},
        default=_default_journal,
        domain="[('type', 'in', {'out_invoice': ['sale'], 'out_refund': ['sale'], 'in_refund': ['purchase'], 'in_invoice': ['purchase']}.get(type, [])), ('company_id', '=', company_id)]")
    kiosk_id = fields.Many2one('stock.location', string='Kiosk *')
    date_start = fields.Datetime(string='Start date')
    date_end = fields.Datetime(string='End date')
    invoice_type = fields.Selection([('rental', 'Rental'), ('sale', 'Sale'), ('loss', 'Loss')], string="Type invoice", default=_default_account_type)
    
    kiosk_id = fields.Many2one('stock.location', string='Kiosk *')
    date_start = fields.Datetime(string='Billing start date')
    date_end = fields.Datetime(string='Billing end date')
    
    def set_in_line(self):
        print 'Error'
    
    
class AccountJournal(models.Model):
        _inherit = "account.journal"
        _sql_constraints = [('code_uniq', 'unique(code)', "A code must be unique !")]