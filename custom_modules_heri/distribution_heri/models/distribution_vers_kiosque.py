# -*- coding: utf-8 -*-

from odoo import fields, models, api
import re
from odoo.exceptions import UserError

class StockPickingDistribution(models.Model):
    _inherit = 'stock.picking'   
    
    @api.depends('location_dest_id')
    def _compute_is_received(self):
        for pick in self:
            if pick.mouvement_type in ('bs','be','bci','prise_en_charge','distribution_vers_kiosque'):
                if pick.location_dest_id.is_kiosque :
                    pick.is_received = True
    observation_colis = fields.Text(string="Observations ")
    
    mouvement_type = fields.Selection([
        ('bs', 'bon de sortie'),
        ('be', 'bon d entree'),
        ('bci', 'Bon de cession Interne'),
        ('br', 'Bon de Retour'),
        ('distribution_vers_kiosque', 'Distribution vers le kiosque'),
        ('prise_en_charge', 'Pris en charge article envoyé par les entrepreneurs'),
        ], string='Type de Mouvement', readonly=True, track_visibility='onchange')
    
    purchase_terminated = fields.Boolean(compute="_compute_purchase_terminated")
    
    @api.multi
    def achat_prestataire(self):
        action = self.env.ref('distribution_heri.action_non_stoke_distribution').read()[0]
        return action
    
    def action_bon_de_sortie_distribution_fonction(self):
        action = self.env.ref('distribution_heri.action_bon_de_sortie_distribution').read()[0]
        return action
    
    def _compute_purchase_terminated(self):
        for order in self:
            current_brq_id = self.env['purchase.order'].search([('picking_bci_id','=',order.id)])
            if current_brq_id and all([x.statut_bex == 'comptabilise' for x in current_brq_id]):
                order.purchase_terminated = True
            else :
                order.purchase_terminated = False
                
    prestataire_count = fields.Float(compute="_compute_prestaire")
    
    @api.multi
    def _compute_prestaire(self):
        for br in self:
            purchase_child = self.env['purchase.order'].search([('picking_bci_id','=',br.id)])
            if purchase_child:
                br.prestataire_count = len(purchase_child)
  
    def envoye_missionnaire(self):
        self.action_confirm()
        self.write({'state':'attente_magasinier'})
    
    def envoyer_magasinier_distribution(self):
        self.action_assign()
        self.write({'state':'dist_visa_magasinier'})

    def etab_bci(self):
        self.action_confirm()
        self.action_assign()
        self.write({'state':'visa_logiste'})
        
    def etab_bci_call(self):
        self.write({'state':'bci_visa_logistique'})
        
    bs_count = fields.Integer(compute='_compute_bs')
    
    @api.multi
    def _compute_bs(self):
        for order in self:
            bs_child= order.env['stock.picking'].search([('picking_bs_id','=',order.id)])
            if bs_child:
                order.bs_count = len(bs_child)
        
    def create_bs_distribution(self):
        StockPickingHeri = self.env['stock.picking']
        move_lines = self.env['stock.move']
        pack_operation_lines = self.env['stock.pack.operation']
        for order in self:
            vals = {
                    'picking_type_id': order.env.ref('purchase_heri.type_preparation_heri').id,
                    'partner_id': order.partner_id.id,
                    'min_date': order.min_date,
                    'origin': order.name,
                    'picking_bs_id' :order.id,
                    'location_dest_id': order.location_dest_id.id,
                    'location_id': order.location_id.id,
                    'company_id': order.company_id.id,
                    'move_type': 'direct',
                    'breq_id' : order.breq_id.id,
                    'employee_id': order.employee_id.id,
                    'section' : order.section,
                    'amount_untaxed' : order.amount_untaxed,
                    'mouvement_type': 'bs',
                    }
            move = StockPickingHeri.create(vals)
            picking_type_id = order.env.ref('purchase_heri.type_preparation_heri').id
            picking_type = self.env['stock.picking.type'].search([('id','=',picking_type_id)])
            picking_type.code = 'internal'
            picking_type.default_location_src_id = order.location_id.id
            picking_type.default_location_dest_id = move.location_dest_id.id
            for line in order.pack_operation_ids:
                template = {
                            'product_id': line.product_id.id,
                            'product_qty': line.product_qty,
                            'qty_done': line.product_qty,
                            'product_uom_id': line.product_uom_id.id,
                            'location_dest_id': order.location_dest_id.id,
                            'location_id': order.location_id.id,
                            'picking_id': move.id,
                            'company_id': move.company_id.id,
                            'procurement_id': False,
                            'origin': move.name,
                            'price_unit' : line.price_unit,
                            'price_subtotal' : line.price_subtotal,
                            }
                pack_operation_lines.create(template)
            for line in order.move_lines:
                template = {
                            'name':order.name,
                            'product_id': line.product_id.id,
                            'product_uom_qty': line.product_uom_qty,
                            'product_uom': line.product_uom.id,
                            'location_dest_id': order.location_dest_id.id,
                            'location_id': order.location_id.id,
                            'picking_id': move.id,
                            'company_id': move.company_id.id,
                            'procurement_id': False,
                            'origin': move.name,
                            'state': 'assigned',
                            }
                move_lines.create(template)
            move.aviser_magasinier_tiers()
                
        return True
class StockMove(models.Model):
    _inherit = 'stock.move'
     
    @api.depends('product_id')
    def _compute_qte_prevu(self):
        for line in self:
            if line.picking_id.mouvement_type in ('bci','distribution_vers_kiosque','prise_en_charge'):
                if not line.location_id:
                    raise UserError("La zone d'emplacement source ne doit pas être vide")
                
                location_src_id = line.location_id
                total_qty_available = 0.0
                total_reserved = 0.0
                liste_picking_ids = []
                
                stock_quant_ids = line.env['stock.quant'].search(['&', ('product_id','=',line.product_id.id), ('location_id','=', location_src_id.id)])
                line_ids = line.env['purchase.order.line'].search([('order_id.is_breq_stock','=', True), ('order_id.state','!=', 'cancel'), \
                                                                   ('product_id','=', line.product_id.id), ('location_id','=', location_src_id.id), \
                                                                   ])
                #recuperer tous les articles reserves dans bci
                bci_ids = line.env['stock.move'].search([('picking_id.mouvement_type','=', 'bci'), \
                                                                       ('picking_id.state','not in', ('draft','done','cancel')), \
                                                                       ('product_id','=', line.product_id.id)
                                                                       ])  
                total_bci_reserved = sum(x.product_uom_qty for x in bci_ids)                                                
                total_reserved = sum(x.product_qty for x in line_ids if x.order_id.bs_id.state not in ('done','cancel'))
                for quant in stock_quant_ids:
                    total_qty_available += quant.qty
                line.qte_prevu = total_qty_available - total_reserved - total_bci_reserved
        
        return True