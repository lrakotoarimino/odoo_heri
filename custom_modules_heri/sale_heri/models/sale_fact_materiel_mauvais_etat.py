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
    _description = "Facturation des materiels retournes en mauvais etat"
    
    bci_count = fields.Integer(compute='_compute_bci_lie') 
    
    @api.multi
    def _compute_bci_lie(self):
        for order in self:
            bci_child= order.env['stock.picking'].search([('sale_order_id','=',order.id),('is_bci_sale_id','=',True)],limit=1)
            if bci_child:
                order.bci_count = len(bci_child)
    
    def action_controle_technicien(self):
        self.write({'state':'controle_technicien'})
        
    def action_materiel_bon_etat(self):
        is_bon_etat = True
        for order in self:
            for line in order.order_line :
                if line.qte_prevu < line.product_uom_qty :
                    raise UserError("Verifiez la quantité demandée par rapport à  la quantité disponible.")
                if line.product_uom_qty <= 0.0:
                    raise UserError("la quantité demandée doit être une valeur positive.")

            order._create_bci(is_bon_etat)
            order.write({'state':'materiel_bon_etat'})
            
    def action_materiel_mauvais_etat(self):
        is_bon_etat = False
        for order in self:
            for line in order.order_line :
                if line.qte_prevu < line.product_uom_qty :
                    raise UserError("Verifiez la quantité demandée par rapport à  la quantité disponible.")
                if line.product_uom_qty <= 0.0:
                    raise UserError("la quantité demandée doit être une valeur positive.")
            order._create_bci(is_bon_etat)
            order.write({'state':'materiel_mauvais_etat'})
        
    @api.multi
    def _create_bci(self, is_bon_etat):
        StockPickingHeri = self.env['stock.picking']
        move_lines = self.env['stock.move']
        for order in self:
            vals = {
                    'picking_type_id': order.env.ref('purchase_heri.type_preparation_heri').id,
                    'partner_id': order.partner_id.id,
                    'min_date': order.date_order,
                    'origin': order.name,
                    'location_dest_id': order.location_id.id,
                    'location_id': order.kiosque_id.id,
                    'company_id': order.company_id.id,
                    'move_type': 'direct',
                    'state':'draft',
                    'employee_id': order.employee_id.id,
                    'sale_order_id' : order.id,
                    'amount_untaxed' : order.amount_untaxed,
                    'is_bci_sale_id': True,
                    'is_bon_etat': is_bon_etat,
                    'mouvement_type': 'bci',
                    }
            move = StockPickingHeri.create(vals)
            res = re.findall("\d+", move.name)
            longeur_res = len(res)
            res_final = res[longeur_res-1]
            bci_name = "BCI" + "".join(res_final)
            move.update({'name': bci_name})
            picking_type_id = order.env.ref('purchase_heri.type_preparation_heri').id
            picking_type = self.env['stock.picking.type'].search([('id','=',picking_type_id)])
            picking_type.code = 'internal'
            picking_type.default_location_src_id = order.kiosque_id.id
            picking_type.default_location_dest_id = order.location_id.id
            for line in order.order_line:
                template = {
                            'name': line.name or '',
                            'product_id': line.product_id.id,
                            'product_uom': line.product_uom.id,
                            'product_uom_qty': line.product_uom_qty,
                            'price_unit': line.price_unit,
                            'location_dest_id': move.location_dest_id.id,
                            'location_id': move.location_id.id,
                            'picking_id': move.id,
                            'state': 'draft',
                            'company_id': move.company_id.id,
                            'procurement_id': False,
                            'origin': move.name,
                            }
                move_lines.create(template)
        return True
 
    #action ouvrir BCI pour retourner les materiels en bon etat lors d'une demande de retour
    @api.multi
    def action_retour_mat_bci_lie(self):
        action = self.env.ref('sale_heri.action_bci_retour_mat_bon_etat')
        result = action.read()[0]
        return result
    #action ouvrir BCI pour retourner les materiels en mauvais etat lors d'une demande de retour
    @api.multi
    def action_bci_lie_materiel_mauvais_etat(self):
        self.action_retour_mat_bci_lie()
        action = self.env.ref('sale_heri.action_bci_retour_mat_mauvais_etat')
        result = action.read()[0]
        return result