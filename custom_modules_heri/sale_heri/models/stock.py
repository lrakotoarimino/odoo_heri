# -*- coding: utf-8 -*-

from odoo import fields, models, api

class StockPickingHeri(models.Model):
    _inherit = 'stock.picking'   
      
    def aviser_magasinier_tiers(self):
        self.action_confirm()
        self.write({'state':'attente_magasinier'})    
    def aviser_logistique(self):
        self.write({'state':'attente_logistique'})  
    def action_aviser_magasinier_bs(self):
        self.action_assign()
        self.write({'state':'assigned'})