# -*- coding: utf-8 -*-

from odoo import fields, models, api
from collections import namedtuple
from odoo.exceptions import UserError
from odoo.tools.float_utils import float_compare
import re

class Regularisation(models.Model):
    _inherit = 'sale.order'
    
    facture_ids = fields.Many2one('account.invoice')
    
#     @api.onchange('partner_id')
#     def _get_facture_impayee(self):
#         account_invoice_ids = self.env['account.invoice'].search([('partner_id','=',self.partner_id.id),('state','not in',('paid','cancel'))]).id
#         self.impayes_ids = account_invoice_ids
    
    def _prepare_ale_order_line_from_invoice_line(self, line):
        data = {
                'order_id': self.id,
                'name': line.product_id.name,
                'sale_line_id':line.id,
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
    @api.onchange('facture_ids')
    def onchange_facture_ids(self):
        new_lines = self.env['sale.order.line']
        for line in self.facture_ids.invoice_line_ids:
            data = self._prepare_ale_order_line_from_invoice_line(line)
            new_line = new_lines.new(data)
            new_lines += new_line

        self.order_line = new_lines
        return {}
    
    def accord_call_center(self):
        attachment_obj = self.env['ir.attachment']
        for order in self:
            attachment_ids = attachment_obj.search([('res_model','=','sale.order'),('res_id','=',order.id)])
            if attachment_ids : 
                self.write({'state':'a_la_finance'})
            else:
                raise UserError("Veuillez d'abord insérer une pièce jointe dans le document pour justificatif.")
            
    def refus_call_center(self):
        self.write({'state':'cancel'})
    def accord_finance(self):
        self.write({'state':'observation_dg'})
    def refus_finance(self):
        self.write({'state':'draft'})
    def accord_DG(self):
        self.write({'state':'facture_au_finance'})
    def refus_DG(self):
        self.write({'state':'draft'})
    def accord_final_finance(self):
        self.write({'state':'valider_par_finance'})
        
    avoir_regularisation_count = fields.Float(compute="_compute_avoir_regularisation_count")
    
    @api.multi
    def _compute_avoir_regularisation_count(self):
        for order in self:
            avoir_regularisation_count_ids = order.env['sale.order'].search([('partner_id','=',order.partner_id.id),('facturation_type','=','regularisation_facture')])
            if avoir_regularisation_count_ids:
                order.avoir_regularisation_count = len(avoir_regularisation_count_ids)
                
    @api.multi
    def action_avoir_regularisation(self):
        action = self.env.ref('sale_heri.action_regularisation_facture').read()[0]
        action['domain'] = [('partner_id', '=', self.partner_id.id),('facturation_type','=','regularisation_facture')]
        return action