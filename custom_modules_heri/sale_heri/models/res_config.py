# -*- coding: utf-8 -*-

from odoo import fields, models, api


class PurchaseConfigSettings(models.TransientModel):
    _inherit = 'sale.config.settings'
    
    seuil_nbr_jour = fields.Float("Seuil du nombre de jour de la facturation redevance mensuelle", default=1)
    seuil_qte_article = fields.Float("Seuil de la quantite d'article de la facture redevance", default=5)
    
#     def set_seuil_nbr_jour_non_prevu(self):
#         waiting_mode = self.env.ref('sale_heri.act_correction_motif_finance_to_observation_dg')
#         waiting_mode.write({'condition': 'nbre_jour_detention > %s' % self.seuil_nbr_jour})
#         sms_invoice = self.env.ref('sale_heri.act_correction_motif_finance_to_verif_pec')
#         sms_invoice.write({'condition': 'nbre_jour_detention <= %s' % self.seuil_nbr_jour})
#         
#     def set_seuil_qte_article(self):
#         waiting_mode = self.env.ref('sale_heri.act_correction_motif_finance_to_observation_dg')
#         waiting_mode.write({'condition': 'product_uom_qty > %s' % self.seuil_qte_article})
#         sms_invoice = self.env.ref('sale_heri.act_correction_motif_finance_to_verif_pec')
#         sms_invoice.write({'condition': 'product_uom_qty <= %s' % self.seuil_qte_article})    