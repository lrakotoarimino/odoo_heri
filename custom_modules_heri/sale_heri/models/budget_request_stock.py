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
    is_breq_id_sale = fields.Boolean('Est un breq stock sale')
    is_facture_comptabilise = fields.Boolean('Est comptabilise',compute="_compute_all_comptabilise")
    
    #creation bon de sortie (budget request stock)
    @api.multi
    def _create_picking3(self):
        StockPickingHeri = self.env['stock.picking']
        for order in self:
            vals = {

                    'picking_type_id': order.env.ref('purchase_heri.type_preparation_heri').id,
                    'partner_id': order.partner_id.id,
                    'date': order.date_order,
                    'origin': order.breq_id_sale.name,
                    'location_dest_id': order.env.ref('purchase_heri.stock_location_virtual_heri').id,
                    'location_id': order.location_id.id,
                    'company_id': order.company_id.id,
                    'move_type': 'direct',
                    'employee_id': order.employee_id.id,
                    'breq_id' : order.id,
                    'section' : order.section,
                    'amount_untaxed' : order.amount_untaxed,
                    'is_bs': True,
                    'mouvement_type' : order.mouvement_type,
                    }
            picking_type_id = order.env.ref('purchase_heri.type_preparation_heri').id
            move = StockPickingHeri.create(vals)
            move_lines = order.order_line._create_stock_moves(move)
            move_lines = move_lines.filtered(lambda x: x.state not in ('done', 'cancel')).action_confirm()
            move_lines.action_assign()
#             move_lines.reception_magasinier()
            
         
        picking_type = self.env['stock.picking.type'].search([('id','=',picking_type_id)])
        picking_type.default_location_src_id = self.location_id.id
        return True
    
    #test
    state = fields.Selection([
        ('nouveau', 'Nouveau'),
        ('confirmation_dg', 'En attente validation DG'),
        ('a_approuver', 'Avis supérieur hiérarchique'),
        ('test', 'Test des matériels'),
        ('etab_facture', 'Etablissement Facture'),
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
    
    statut_facture = fields.Selection(compute="_get_statut_facture", string='Etat Facture',
                      selection=[
                             ('draft', 'Nouveau'), ('cancel', 'Cancelled'),
                             ('open','Ouvert'),
                             ('paid','Comptabilise'),
                             ])
    @api.one
    def _get_statut_facture(self):  
        facture_lie = self.env['account.invoice'].search([('breq_stock_id','=',self.id)], limit=1)
        if facture_lie:
            self.statut_facture = facture_lie.state     
    
    @api.depends('state')
    def _compute_all_comptabilise(self):
        for order in self:
            current_brq_stock_id = self.env['account.invoice'].search([('breq_stock_id','=',order.id)])
            if current_brq_stock_id and all([x.state == 'paid' for x in current_brq_stock_id]):
                order.is_facture_comptabilise = True
            else :
                order.is_facture_comptabilise = False 

    def envoyer_pour_tester(self):
        self._create_picking3()
        self.write({'state':'test'})  
    def annule_test(self):
        self.write({'state':'nouveau'})
    def envoyer_pour_facturation(self):
        self.write({'state':'etab_facture'}) 
        self._create_facture_breq_stock()
    def annule_facturation(self):
        self.write({'state':'nouveau'})  
    def comptabiliser_sale(self):
        self.write({'state':'comptabilise'})

    breq_facture_stock_ids = fields.One2many('account.invoice', string="Breq facture ids", compute='_compute_breq_stock_facture_lie')
    breq_facture_stock_count = fields.Integer(compute='_compute_breq_stock_facture_lie') 
    
    #facture lié count 
    @api.multi
    def _compute_breq_stock_facture_lie(self):
        for order in self:
            breq_stock_facture_child= order.env['account.invoice'].search([('breq_stock_id','=',order.id)],limit=1)
            if breq_stock_facture_child:
                order.breq_facture_stock_ids = breq_stock_facture_child
                order.breq_facture_stock_count = len(breq_stock_facture_child)
                
    #facture lié vue
    @api.multi
    def action_breq_stock_lie_facture(self):
        action = self.env.ref('sale_heri.action_budget_request_stock_heri_lie_facture')
        result = action.read()[0]
        return result
    
    #création facture
    @api.multi
    def _create_facture_breq_stock(self):
        breq_stock_facture_obj = self.env['account.invoice']
        for order in self:
            vals = {
                    'name': order.name or order.name,
                    'origin': order.breq_id_sale.name,
                    'type': 'out_invoice',
                    'reference': False,
                    'account_id': order.partner_id.property_account_receivable_id.id,
                    'partner_id': order.partner_id.id,
                    'payment_term_id': order.payment_term_id.id,
                    'fiscal_position_id': order.fiscal_position_id.id or order.partner_id.property_account_position_id.id,
                    'breq_stock_id': order.id, 
                    'parent_id':order.breq_id_sale,
                    'partner_id': order.partner_id.id,
                    'user_id': order.employee_id.id,                   
                    'amount_total': order.amount_untaxed,
                    'date_invoice':fields.Datetime.now(),
                    }
            breq_facture_id = breq_stock_facture_obj.create(vals)     
            breq_facture_lines = order.order_line._create_facture_breq_stock_lines(breq_facture_id)
        return True
    
    #action form bon de sortie facturation aux tiers
    @api.multi
    def action_bs_lie_facturation_tiers(self):
        action = self.env.ref('sale_heri.action_bon_de_sortie_lie_facture_tiers')
        result = action.read()[0]
        return result

class PurchaseOrderLineHeri(models.Model):
    _inherit = 'purchase.order.line'
     
    @api.multi
    def _create_facture_breq_stock_lines(self, breq_facture_id):
        breq_facture_line = self.env['account.invoice.line']
        for line in self:
            vals = {
                'name': line.name or '',
                'product_id': line.product_id.id,
                'quantity' : line.product_qty,
                'price_unit': line.price_unit,
                'price_subtotal' : line.price_subtotal,
                'account_id': 1,
                'invoice_id': breq_facture_id.id,  
#                 'purchase_type': line.order_id.purchase_type,
            }     
            breq_facture_lines = breq_facture_line.create(vals)
        return True
    
class AccountInvoiceHeri(models.Model):
    _inherit = 'account.invoice'
     
    breq_stock_id = fields.Many2one('purchase.order')
    
    def print_duplicata(self):
        return self.env["report"].get_action(self, 'account.account_invoice_report_duplicate_main')
    
# class StockMoveHeri(models.Model):
#     _inherit = 'stock.move'
#      
#     state = fields.Selection([
#         ('draft', 'New'), ('cancel', 'Cancelled'),
#         ('attente_logistique', 'Avis logistique'),('attente_magasinier', 'Avis magasinier'),
#         ('waiting', 'Waiting Another Move'), ('confirmed', 'Waiting Availability'),
#         ('assigned', 'Available'), ('done', 'Done')], string='Status',
#         copy=False, default='draft', index=True, readonly=True,
#         help="* New: When the stock move is created and not yet confirmed.\n"
#              "* Waiting Another Move: This state can be seen when a move is waiting for another one, for example in a chained flow.\n"
#              "* Waiting Availability: This state is reached when the procurement resolution is not straight forward. It may need the scheduler to run, a component to be manufactured...\n"
#              "* Available: When products are reserved, it is set to \'Available\'.\n"
#              "* Done: When the shipment is processed, the state is \'Done\'.")
#      
#     def reception_magasinier(self):
#         self.write({'state':'attente_magasinier'})
#      
# class StockPickingHeri(models.Model):
#     _inherit = 'stock.picking'   
#      
#     def aviser_logistique(self):
#         self.action_confirm()
#         self.write({'state':'attente_logistique'})    
# 
#     def action_aviser_magasinier_bs(self):
#         self.action_assign()
#         self.write({'state':'assigned'})
    
