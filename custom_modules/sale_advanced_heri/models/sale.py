# -*- coding: utf-8 -*-

from odoo import api, fields, models


class SaleOrder(models.Model):
    _inherit = "sale.order"
    
    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('sent', 'Proforma'),
        ('sale', u'Validé'),
        ('done', 'Terminé'),
        ('cancel', 'Annulé'),
        ], string='Status', readonly=True, copy=False, index=True, track_visibility='onchange', default='draft')
    
    # redefinition
    @api.multi
    def _prepare_invoice(self):
        invoice_data = super(SaleOrder, self)._prepare_invoice()
        invoice_data['invoice_type'] = 'sale'
        return invoice_data


class SaleAdvancePaymentInv(models.TransientModel):
    _inherit = "sale.advance.payment.inv"
    
    # redefinition
    @api.multi
    def _create_invoice(self, order, so_line, amount):
        invoice = super(SaleAdvancePaymentInv, self)._create_invoice(order, so_line, amount)
        invoice.invoice_type = 'sale'
        return invoice