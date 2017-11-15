# -*- coding: utf-8 -*-

from odoo import fields, models, api
from collections import namedtuple
from odoo.exceptions import UserError
from odoo.tools.float_utils import float_compare
import re
import time
from docutils.nodes import Invisible

class BreqStockHeri(models.Model):
    _inherit = "purchase.order"
    
    breq_id_sale = fields.Many2one("sale.order")
    
    state = fields.Selection([
        ('nouveau', 'Nouveau'),
        ('confirmation_dg', 'En attente validation DG'),
        ('a_approuver', 'Avis supérieur hiérarchique'),
        ('avis_magasinier', 'Avis Magasinier'),
        ('test', 'Test Materiel'),
        ('etab_facture', 'Etablissement Facture'),
        ('edition_et_visa', 'Visa'),
        ('edition', 'Edition'),
        ('comptabilise', 'Comptabilise'),
        ('aviser_finance', 'Etablissement OV'),
        ('ov_to_bank', 'OV envoyé à la banque'),
        ('br_lie', 'Prix de revient'),
        ('calcul_pr', 'Prix de revient calculé'),
        ('non_prevue', 'En vérification compta'),
        ('attente_validation', 'En attente validation DG'),
        ('wait_mode', 'En attente paiement finance'),
        ('purchase', 'BEX'),
        ('refuse', 'Refusé'),
        ('done', 'Terminé'),
        ('bs', 'Bon de sortie'),
        ('cancel', 'Annulé'),
        ], string='Etat BReq', readonly=True, default='nouveau', track_visibility='onchange')
            
    def envoyer_magasinier(self):
        self.write({'state':'avis_magasinier'}) 
    def envoyer_pour_tester(self):
        self.write({'state':'test'}) 
    def annule_test(self):
        self.write({'state':'nouveau'})
    def envoyer_pour_facturation(self):
        self.write({'state':'etab_facture'}) 
#         self._create_facture_breq_stock()
    def annule_facturation(self):
        self.write({'state':'avis_magasinier'}) 
    def edition_et_visa(self):
        self.write({'state':'edition_et_visa'}) 
    def annule_edition_et_visa(self):
        self.write({'state':'test'})
    def edition_finance(self):
        self.write({'state':'edition'}) 
    def annule_edition_finance(self):
        self.write({'state':'etab_facture'}) 
    def comptabiliser_sale(self):
        self._create_picking2()
        self.write({'state':'comptabilise'})
    def annule_comptabiliser_sale(self):
        self.write({'state':'edition_et_visa'}) 
    
#     breq_facture_stock_ids = fields.Many2many('account.invoice', string="Breq facture ids", compute='_compute_breq_stock_facture_lie')
#     breq_facture_stock_count = fields.Integer(compute='_compute_breq_stock_facture_lie') 
#     
#     @api.multi
#     def _compute_breq_stock_facture_lie(self):
#         for order in self:
#             breq_stock_facture_child= order.env['account.invoice'].search([('breq_stock_id','=',order.id)],limit=1)
#             if breq_stock_facture_child:
#                 order.breq_stock_ids = breq_stock_facture_child
#                 order.breq_stock_count = len(breq_stock_facture_child)
#     @api.multi
#     def action_breq_stock_lie_facture(self):
#         action = self.env.ref('sale.action_budget_request_stock_heri_lie_facture')
#         result = action.read()[0]
#         return result
#     
#     @api.multi
#     def _create_facture_breq_stock(self):
#         breq_stock_facture_obj = self.env['account.invoice']
#         for order in self:
#             vals = {
#                     'breq_stock_id': order.id, 
#                     'partner_id': order.partner_id.id,
#                     'user_id': order.employee_id.id,                   
#                     'amount_total': order.amount_total,
#                     'date_invoice':fields.Datetime.now(),
#                     }
#             breq_facture_id = breq_stock_facture_obj.create(vals)     
#             breq_facture_lines = order.order_line._create_facture_breq_stock_lines(breq_facture_id)
#         return True

# class PurchaseOrderLineHeri(models.Model):
#     _inherit = 'purchase.order.line'
#     
#     @api.multi
#     def _create_facture_breq_stock_lines(self, breq_facture_id):
#         breq_facture_line = self.env['account.invoice.line']
#         for line in self:
#             vals = {
#                 'name': line.name or '',
#                 'product_id': line.product_id.id,
#                 'quantity' : line.product_qty,
#                 'price_unit': line.price_unit,
#                 'price_subtotal' : line.price_subtotal,
#                 'account_id': breq_facture_id.id,
#                 
# #                 'purchase_type': line.order_id.purchase_type,
#             }     
#             breq_facture_lines = breq_facture_line.create(vals)
#         return True
# class AccountInvoiceHeri(models.Model):
#     _inherit = 'account.invoice'
#     
#     breq_stock_id = fields.Many2one('purchase.order')