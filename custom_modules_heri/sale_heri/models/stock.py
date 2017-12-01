# -*- coding: utf-8 -*-

from odoo import fields, models, api

class StockPickingHeri(models.Model):
    _inherit = 'stock.picking'   

    date_arrivee_reelle = fields.Datetime(string="Date d'arrivée réelle des matériels")  
    sale_order_id = fields.Many2one('sale.order', string='Sale Order')
    is_bci_sale_id = fields.Boolean('Est un bci venant sale order ?') 
    is_bon_etat = fields.Boolean('Le materiel est-il en bon etat ?') 
    breq_stock_count = fields.Integer(compute='_compute_breq_stock_lie') 
     
    @api.multi
    def _compute_breq_stock_lie(self):
        for order in self:
            breq_child= order.env['purchase.order'].search([('is_from_bci','=',True),('picking_bci_id','=',order.id)],limit=1)
            if breq_child:
                order.breq_stock_count = len(breq_child)
    def aviser_magasinier_tiers(self):
        self.action_confirm()
        self.write({'state':'attente_magasinier'})    
    def aviser_logistique(self):
        self.write({'state':'attente_logistique'})  
    def action_aviser_magasinier_bs(self):
        self.action_assign()
        self.write({'state':'assigned'})
    def action_breq_stock_lie_materiel_mauvais_etat(self):
        action = self.env.ref('sale_heri.action_budget_request_stock_lie')
        result = action.read()[0]
        return result