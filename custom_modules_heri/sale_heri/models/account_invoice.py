# -*- coding: utf-8 -*-
from odoo import api, fields, models

class AccountInvoiceHeri(models.Model):
    _inherit = 'account.invoice'
     
    breq_stock_id = fields.Many2one('purchase.order')
    breq_id_sale = fields.Many2one('sale.order')
    state = fields.Selection([
            ('draft','Draft'),
            ('proforma', 'Pro-forma'),
            ('proforma2', 'Pro-forma'),
            ('attente_envoi_sms', 'Attente d\'envoi SMS'),
            ('pour_visa','Visa'),
            ('open', 'Open'),
            ('paid', 'Paid'),
            ('cancel', 'Cancelled'),
        ], string='Status', index=True, readonly=True, default='draft',
        track_visibility='onchange', copy=False,
        help=" * The 'Draft' status is used when a user is encoding a new and unconfirmed Invoice.\n"
             " * The 'Pro-forma' status is used when the invoice does not have an invoice number.\n"
             " * The 'Open' status is used when user creates invoice, an invoice number is generated. It stays in the open status till the user pays the invoice.\n"
             " * The 'Paid' status is set automatically when the invoice is paid. Its related journal entries may or may not be reconciled.\n"
             " * The 'Cancelled' status is used when user cancel invoice.")

    def action_aviser_callcenter(self):
        self.write({'state':'attente_envoi_sms'})
    
    def action_envoi_sms(self):
        self.write({'state':'open'})
    
    def action_pour_visa(self):
        self.action_invoice_open()
        self.write({'state':'open'})
    
    def action_envoi_sms(self):
#         to_open_invoices = self.filtered(lambda inv: inv.state != 'open')
#         if to_open_invoices.filtered(lambda inv: inv.state not in ['proforma2', 'draft', 'attente_envoi_sms']):
#             raise UserError(_("Invoice must be in draft or Pro-forma state in order to validate it."))
#         to_open_invoices.action_date_assign()
#         to_open_invoices.action_move_create()
#         to_open_invoices.invoice_validate()
#         self.write({'state':'open'})
    
        # lots of duplicate calls to action_invoice_open, so we remove those already open
        to_open_invoices = self.filtered(lambda inv: inv.state != 'open')
        to_open_invoices.write({'state':'draft'})
        return self.action_invoice_open()

    def imprimer_facture_redevance_duplicata(self):
        self.print_duplicata()
            
    def print_duplicata(self):
        return self.env["report"].get_action(self, 'account.account_invoice_report_duplicate_main')