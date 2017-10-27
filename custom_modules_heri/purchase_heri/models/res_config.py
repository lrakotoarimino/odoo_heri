# -*- coding: utf-8 -*-

from odoo import fields, models


class PurchaseConfigSettings(models.TransientModel):
    _inherit = 'purchase.config.settings'
    
    seuil_prevu = fields.Float("Seuil d'un budget request achat prévu", default=2000000.0)
    seuil_non_prevu = fields.Float("Seuil d'un budget request achat non prévu", default=200000.0)
    
#     @api.multi
#     def set_default_seuil_prevu(self):
#         #check = self.env.user.has_group('base.group_system')
#         #Values = check and self.env['ir.values'].sudo() or self.env['ir.values']
#         Values = self.env['ir.values']
#         for config in self:
#             Values.set_default('purchase.config.settings', 'seuil_prevu', config.seuil_prevu)
    
    def set_seuil_prevu(self):
        waiting = self.env.ref('purchase_heri.act_prevu_to_act_attente_validation')
        waiting.write({'condition': 'amount_untaxed > %s' % self.seuil_prevu})
        waiting_mode = self.env.ref('purchase_heri.act_prevu_to_act_wait_mode')
        waiting_mode.write({'condition': 'amount_untaxed <= %s' % self.seuil_prevu})
    
    def set_seuil_non_prevu(self):
        waiting_mode = self.env.ref('purchase_heri.act_attente_validation_to_act_wait_mode2')
        waiting_mode.write({'condition': 'amount_untaxed <= %s' % self.seuil_non_prevu})