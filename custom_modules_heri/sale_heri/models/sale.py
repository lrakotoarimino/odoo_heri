# -*- coding: utf-8 -*-

from odoo import fields, models, api
from collections import namedtuple
from odoo.exceptions import UserError
from odoo.tools.float_utils import float_compare
import re
import time

class SaleHeri(models.Model):
    _inherit = "sale.order"
    _description = "Facturation redevance mensuelle"
    
    kiosque_id = fields.Many2one('stock.location', string='Kiosque') 
    
#     @api.onchange('kiosque_id')
#     def onchange_ki
    partner_id = fields.Many2one('res.partner', string='Customer', readonly=True, states={'draft': [('readonly', False)], 'sent': [('readonly', False)],'nouveau': [('readonly', False)]}, required=True, change_default=True, index=True, track_visibility='always')
    state = fields.Selection([
        ('draft', 'Quotation'),
        ('nouveau', 'Generation liste'),
        ('correction_et_motif', 'Correction et Motif'),
        ('correction_et_motif_finance', 'Correction et Motif'),
        ('observation_dg', 'Observation du DG'),
        ('verif_pec', 'Verification des PEC'),
        ('facture_generer', 'Facture Generee'),
        ('sent', 'Quotation Sent'),
        ('sale', 'Facture Generee'),
        ('done', 'Locked'),
        ('cancel', 'Cancelled'),
        ], string='Status', readonly=True, copy=False, index=True, track_visibility='onchange',default='nouveau')
    
    def generation_list(self):
        self.write({'state':'nouveau'})
    def correction_motif_call(self):
        self.write({'state':'correction_et_motif'}) 
    def correction_motif_finance(self):
        self.write({'state':'correction_et_motif_finance'}) 
    def observation_dg(self):
        self.write({'state':'observation_dg'}) 
    def verif_pec(self):
        self.write({'state':'verif_pec'}) 
    def generation_facture_sms(self):
        for order in self:
            order.state = 'sale'
            order.confirmation_date = fields.Datetime.now()
            if self.env.context.get('send_email'):
                self.force_quotation_send()
            #order.order_line._action_procurement_create()
        if self.env['ir.values'].get_default('sale.config.settings', 'auto_done_setting'):
            self.action_done()
        return True
        
class AccountInvoiceHeri(models.Model):
    _inherit = "account.invoice"
    
    state = fields.Selection([
            ('draft','Draft'),
            ('proforma', 'Pro-forma'),
            ('proforma2', 'Pro-forma'),
            ('open', 'Etablissement facture originale'),
            ('paid', 'Paid'),
            ('cancel', 'Cancelled'),
        ], string='Status', index=True, readonly=True, default='draft',
        track_visibility='onchange', copy=False,
        help=" * The 'Draft' status is used when a user is encoding a new and unconfirmed Invoice.\n"
             " * The 'Pro-forma' status is used when the invoice does not have an invoice number.\n"
             " * The 'Open' status is used when user creates invoice, an invoice number is generated. It stays in the open status till the user pays the invoice.\n"
             " * The 'Paid' status is set automatically when the invoice is paid. Its related journal entries may or may not be reconciled.\n"
             " * The 'Cancelled' status is used when user cancel invoice.")

class SaleAdvancePaymentInvHeri(models.TransientModel):
    _inherit = "sale.advance.payment.inv"
    
    @api.multi
    def create_invoices(self):
        sale_orders = self.env['sale.order'].browse(self._context.get('active_ids', []))
        sale_orders.generation_facture_sms()
        if self.advance_payment_method == 'all':
            sale_orders.action_invoice_create(final=True)
        else:
            # Create deposit product if necessary
            if not self.product_id:
                vals = self._prepare_deposit_product()
                self.product_id = self.env['product.product'].create(vals)
                self.env['ir.values'].sudo().set_default('sale.config.settings', 'deposit_product_id_setting', self.product_id.id)

            sale_line_obj = self.env['sale.order.line']
            for order in sale_orders:
                if self.advance_payment_method == 'percentage':
                    amount = order.amount_untaxed * self.amount / 100
                else:
                    amount = self.amount
                if self.product_id.invoice_policy != 'order':
                    raise UserError('The product used to invoice a down payment should have an invoice policy set to "Ordered quantities". Please update your deposit product to be able to create a deposit invoice.')
                if self.product_id.type != 'service':
                    raise UserError("The product used to invoice a down payment should be of type 'Service'. Please use another product or update this product.")
                if order.fiscal_position_id and self.product_id.taxes_id:
                    tax_ids = order.fiscal_position_id.map_tax(self.product_id.taxes_id).ids
                else:
                    tax_ids = self.product_id.taxes_id.ids
                so_line = sale_line_obj.create({
                    'name': 'Advance: %s' % (time.strftime('%m %Y'),),
                    'price_unit': amount,
                    'product_uom_qty': 0.0,
                    'order_id': order.id,
                    'discount': 0.0,
                    'product_uom': self.product_id.uom_id.id,
                    'product_id': self.product_id.id,
                    'tax_id': [(6, 0, tax_ids)],
                })
                self._create_invoice(order, so_line, amount)
        if self._context.get('open_invoices', False):
            return sale_orders.action_view_invoice()
        sale_orders.generation_facture_sms()
        return {'type': 'ir.actions.act_window_close'}