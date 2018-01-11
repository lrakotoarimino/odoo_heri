# -*- coding: utf-8 -*-

from odoo import fields, models, api
from collections import namedtuple
from odoo.exceptions import UserError, RedirectWarning, ValidationError
from odoo.tools.float_utils import float_compare
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.tools.translate import _
import re
import time
from docutils.nodes import Invisible
from datetime import datetime, date
from pyparsing import lineEnd

class SaleHeri(models.Model):
    _inherit = "sale.order"
    _description = "Rééchelonnement des impayés"
    
    invoices_id = fields.Many2one('account.invoice', string="Les impayés à rééchelonner")
    
#     @api.onchange('partner_id')
#     def _get_facture_impayee(self):
#         account_invoice_ids = self.env['account.invoice'].search([('partner_id','=',self.partner_id.id),('state','not in',('paid','cancel'))]).id
#         self.invoices_id = account_invoice_ids

    @api.multi
    def _prepare_invoice(self):
        invoice_vals = super(SaleHeri, self)._prepare_invoice()
        invoice_vals['is_reechelonnement'] = True
        return invoice_vals
        
    def _prepare_invoice_line_from_invoice_line(self, line):
        invoice_line = self.env['sale.order.line']
        data = {
            'order_id': self.id,
            'sale_line_id': line.id,
            'name': line.product_id.name,
            'origin': line.invoice_id.name,
            'product_uom': line.uom_id.id,
            'product_id': line.product_id.id,
            'price_unit': line.price_unit,
            'product_uom_qty': line.quantity,
            'layout_category_id': line.layout_category_id.id,
            'account_analytic_id': line.account_analytic_id.id,
            'analytic_tag_ids': line.analytic_tag_ids.ids,
            'tax_id': line.invoice_line_tax_ids.ids,
            'customer_lead': 0.0
        }
        return data
    
    #Remplir la ligne de la demande par la ligne de la facture a reechelonner
    @api.onchange('invoices_id')
    def onchange_invoices_id(self):
        new_lines = self.env['sale.order.line']
        for line in self.invoices_id.invoice_line_ids:
            data = self._prepare_invoice_line_from_invoice_line(line)
            new_line = new_lines.new(data)
            new_lines += new_line

        self.order_line = new_lines
        return {}
    
    def action_etab_reechelonnement(self):
        self.write({'state':'draft'})
    
    def action_observation_finance(self):
        self.write({'state':'attente_finance'})
        
    def action_observation_dg(self):
        self.write({'state':'observation_dg'})
            
    def generation_facture_reechelonnement(self):
        self.action_confirm()
        
    @api.multi
    def action_impayes(self):
        action = self.env.ref('sale_heri.action_impayes').read()[0]
        action['domain'] = [('partner_id', '=', self.partner_id.id), ('state', 'not in', ('paid','cancel')), ('is_reechelonnement', '=', False)]
        return action
    
    @api.multi
    def action_confirm(self):
        for order in self:
            order.state = 'sale'
            order.confirmation_date = fields.Datetime.now()
            if self.env.context.get('send_email'):
                self.force_quotation_send()
            #Empêcher la création du bon de livraison pour le rééchelonnement des ampayés cqr il n'y a pas d'article à livrer
            if order.facturation_type != 'reechelonnement_impayes':
                order.order_line._action_procurement_create()
        if self.env['ir.values'].get_default('sale.config.settings', 'auto_done_setting'):
            self.action_done()
        return True
    
class SaleOrderLineHeri(models.Model):
    """ Override AccountInvoice_line to add the link to the sale order line it is related to"""
    _inherit = 'sale.order.line'

    sale_line_id = fields.Many2one('account.invoice.line', 'Sale Order Line', ondelete='set null', index=True, readonly=True)
    sale_id = fields.Many2one('account.invoice', related='sale_line_id.invoice_id', string='Sale Order', store=False, readonly=True,
        help='Associated Sale Order. Filled in automatically when a SO is chosen on the vendor bill.')