# -*- coding: utf-8 -*-

from odoo import fields, models, api
from collections import namedtuple
from odoo.exceptions import UserError
from odoo.tools.float_utils import float_compare
import re

class ModePaiement(models.Model):
    _name = "a.facturer"
    
    a_facturer= fields.Float('Pourcentage')
    breq_id = fields.Many2one('purchase.order')
    #mode de paiement
    def valider_pourcentage_a_facturer(self):
        #self._compute_pump()
        if not self.a_facturer:
            raise UserError(u'Le pourcentage de montant ne doit pas être vide.')
        if self.a_facturer > 100:
            raise UserError(u'Le pourcentage de montant ne doit pas être superieur à 100%.')
        if self.a_facturer < 0:
            raise UserError(u'Le pourcentage de montant ne doit pas être negatif')
        breq = self.env['purchase.order'].browse(self.breq_id.id)
        for br in breq :
            br.amount_untaxed = (br.amount_untaxed * self.a_facturer)/100
            for line in br.order_line :
                line.price_unit = (line.price_unit * self.a_facturer)/100
                breq.write({'line.price_unit': line.price_unit})
            breq.write({'br.amount_untaxed': br.amount_untaxed})
        breq.write({'a_facturer_pourcentage': self.a_facturer})
        breq.write({'state': 'etab_facture'})
        res = re.findall("\d+", breq.name)
        longeur_res = len(res)
        res_final = res[longeur_res-1]
        facture_name = "Facturer" + "".join(res_final)
        facture_name_update = facture_name + " pour " + str(self.a_facturer) + " % "
        breq.update({'name': facture_name_update})