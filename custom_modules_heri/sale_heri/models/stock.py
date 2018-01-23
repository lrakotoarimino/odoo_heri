# -*- coding: utf-8 -*-

from odoo import fields, models, api
import re

class StockPickingHeri(models.Model):
    _inherit = 'stock.picking'   
    #stock heri
    is_bon_etat = fields.Boolean('Le materiel est-il en bon etat ?')
    date_arrivee_reelle = fields.Datetime(string="Date d'arrivée réelle des matériels")  
    location_id = fields.Many2one(
        'stock.location', "Source Location Zone",
        default=lambda self: self.env['stock.picking.type'].browse(self._context.get('default_picking_type_id')).default_location_src_id,
        readonly=True,
        states={'draft': [('readonly', False)]})
    location_dest_id = fields.Many2one(
        'stock.location', "Destination Location Zone",
        default=lambda self: self.env['stock.picking.type'].browse(self._context.get('default_picking_type_id')).default_location_dest_id,
        readonly=True,
        states={'draft': [('readonly', False)],'attente_magasinier': [('readonly', False)]})
    state = fields.Selection([
        ('draft', 'Draft'), ('cancel', 'Cancelled'),
        ('attente_hierarchie','Avis supérieur hierarchique'),
        ('attente_call_center','Avis call center'),
        ('attente_finance','Avis Finance'),
        ('attente_logistique','Avis logistique'),
        ('attente_magasinier','Avis Magasinier'),
        ('visa_logiste','visa logistique'),
        ('visa_call_center','Avis call center'),
        ('dist_visa_magasinier','Visa Magasinier'),
        ('bci_visa_logistique','Visa Logistique'),
        ('waiting', 'Waiting Another Operation'),
        ('confirmed', 'Waiting Availability'),
        ('partially_available', 'Partially Available'),
        ('assigned', 'Available'), ('done', 'Done')], string='Status', compute='_compute_state',
        copy=False, index=True, readonly=True, store=True, track_visibility='onchange',
        help=" * Draft: not confirmed yet and will not be scheduled until confirmed\n"
             " * Waiting Another Operation: waiting for another move to proceed before it becomes automatically available (e.g. in Make-To-Order flows)\n"
             " * Waiting Availability: still waiting for the availability of products\n"
             " * Partially Available: some products are available and reserved\n"
             " * Ready to Transfer: products reserved, simply waiting for confirmation.\n"
             " * Transferred: has been processed, can't be modified or cancelled anymore\n"
             " * Cancelled: has been cancelled, can't be confirmed anymore")
    
    sale_order_id = fields.Many2one('sale.order', string='Sale Order')
    is_bci_sale_id = fields.Boolean('Est un bci venant sale order ?')  
    breq_stock_count = fields.Integer(compute='_compute_breq_stock_lie') 
    picking_bs_id = fields.Many2one('stock.picking')
     
    @api.multi
    def _compute_breq_stock_lie(self):
        for order in self:
            breq_child= order.env['purchase.order'].search([('is_from_bci','=',True),('picking_bci_id','=',order.id)],limit=1)
            if breq_child:
                order.breq_stock_count = len(breq_child)
                
    bs_count = fields.Integer(compute='_compute_bs')
    @api.multi
    def _compute_bs(self):
        for order in self:
            bs_child= order.env['stock.picking'].search([('picking_bs_id','=',order.id)])
            if bs_child:
                order.bs_count = len(bs_child)
    

    def aviser_magasinier_tiers(self):
        self.action_confirm()
        self.write({'state':'attente_magasinier'})   
        
    def action_aviser_logistique_retour_mat(self): 
        self.write({'state':'attente_logistique'})  
        
    def action_aviser_finance(self):
        self.write({'state':'attente_finance'})  
      
    def aviser_call_center(self):
        self.write({'state':'attente_call_center'})  
           
    def aviser_logistique(self):
        self.write({'state':'visa_logiste'})  
    def aviser_logistique_perte(self):
        self.write({'state':'attente_logistique'})
    def action_aviser_magasinier_bs(self):
        self.action_assign()
        self.write({'state':'assigned'})

    def action_aviser_call_center_bs(self):
        self.write({'state':'visa_call_center'})
        
    def action_validation_call_center_bs(self):
        self.write({'state':'assigned'})
        
    def action_breq_stock_lie_materiel_mauvais_etat(self):
        action = self.env.ref('sale_heri.action_budget_request_stock_lie')
        result = action.read()[0]
        return result
    is_bs_create = fields.Boolean('Bs créer')
    @api.multi
    def _create_bon_de_sortie(self):
        StockPickingHeri = self.env['stock.picking']
        move_lines = self.env['stock.move']
        pack_operation_lines = self.env['stock.pack.operation']
        for order in self:
            vals = {
                    'picking_type_id': order.picking_type_id.id,
                    'partner_id': order.partner_id.id,
                    'min_date': order.min_date,
                    'origin': order.name,
                    'picking_bs_id' :order.id,
                    'location_dest_id': order.env.ref('sale_heri.stock_location_virtual_client').id,
                    'location_id': order.location_dest_id.id,
                    'company_id': order.company_id.id,
                    'move_type': 'direct',
                    'breq_id' : order.breq_id.id,
                    'employee_id': order.employee_id.id,
                    'section' : order.section,
                    'amount_untaxed' : order.amount_untaxed,
                    'mouvement_type': 'bs',
                    }
            move = StockPickingHeri.create(vals)
            picking_type_id = order.picking_type_id.id,
            picking_type = self.env['stock.picking.type'].search([('id','=',picking_type_id)])
            picking_type.code = 'internal'
            picking_type.default_location_src_id = order.location_id.id
            picking_type.default_location_dest_id = order.location_dest_id.id
            for line in order.pack_operation_ids:
                template = {
                            'product_id': line.product_id.id,
                            'product_qty': line.product_qty,
                            'qty_done': line.qty_done,
                            'product_uom_id': line.product_uom_id.id,
                            'location_dest_id': order.env.ref('sale_heri.stock_location_virtual_client').id,
                            'location_id': order.location_dest_id.id,
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
                            'location_dest_id': order.env.ref('sale_heri.stock_location_virtual_client').id,
                            'location_id': order.location_dest_id.id,
                            'picking_id': move.id,
                            'company_id': move.company_id.id,
                            'procurement_id': False,
                            'origin': move.name,
                            'state': 'assigned',
                            }
                move_lines.create(template)
            move.aviser_magasinier_tiers()
                
        return True
    
    @api.multi
    def _create_bon_de_sortie_perte(self):
        StockPickingHeri = self.env['stock.picking']
        move_lines = self.env['stock.move']
        pack_operation_lines = self.env['stock.pack.operation']
        for order in self:
            vals = {
                    'picking_type_id': order.picking_type_id.id,
                    'partner_id': order.partner_id.id,
                    'min_date': order.min_date,
                    'origin': order.name,
                    'picking_bs_id' :order.id,
                    'location_dest_id': order.env.ref('sale_heri.stock_location_virtual_client').id,
                    'location_id': order.location_dest_id.id,
                    'company_id': order.company_id.id,
                    'move_type': 'direct',
                    'employee_id': order.employee_id.id,
                    'breq_id' : order.breq_id.id,
                    'section' : order.section,
                    'amount_untaxed' : order.amount_untaxed,
                    'mouvement_type': 'bs',
                    }
            move = StockPickingHeri.create(vals)
            picking_type_id =order.picking_type_id.id,
            picking_type = self.env['stock.picking.type'].search([('id','=',picking_type_id)])
            picking_type.code = 'internal'
            picking_type.default_location_src_id = order.location_id.id
            picking_type.default_location_dest_id = order.location_dest_id.id
            for line in order.pack_operation_ids:
                template = {
                            'product_id': line.product_id.id,
                            'product_qty': line.product_qty,
                            'qty_done': line.qty_done,
                            'product_uom_id': line.product_uom_id.id,
                            'location_dest_id': order.env.ref('sale_heri.stock_location_virtual_client').id,
                            'location_id': order.location_dest_id.id,
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
                            'location_dest_id': order.env.ref('sale_heri.stock_location_virtual_client').id,
                            'location_id': order.location_dest_id.id,
                            'picking_id': move.id,
                            'company_id': move.company_id.id,
                            'procurement_id': False,
                            'origin': move.name,
                            'state': 'assigned',
                            }
                move_lines.create(template)
            move.aviser_logistique_perte()
                
        return True
    
    def create_bs_bci_perte(self):
        self.is_bs_create = True
        self._create_bon_de_sortie_perte()
        
    def create_bs_bci(self):
        self.is_bs_create = True
        self._create_bon_de_sortie()
        
    def action_bon_de_sortie_bci(self):
        action = self.env.ref('sale_heri.action_bon_de_sortie')
        result = action.read()[0]
        return result
    
    def action_bon_de_sortie_perte(self):
        action = self.env.ref('sale_heri.action_bon_de_sortie_perte')
        result = action.read()[0]
        return result
    
    @api.multi
    def do_print_bon_de_cession(self):
        return self.env["report"].get_action(self, 'sale_heri.report_bon_de_cession_interne_template')
    
    @api.multi
    def do_print_BCI(self):
        employee_id = self.env['hr.employee'].search([('user_id','=',self.env.uid)])
        if employee_id:
            self.magasinier_id = employee_id[0].id
        self.do_new_transfer()
        return self.do_print_bon_de_cession()
    