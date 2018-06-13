# -*- coding: utf-8 -*-

from odoo import fields, models
from odoo.exceptions import ValidationError
 
class cnaps(models.Model):
    _name = "cnaps"
    _description = "Etat CNAPS"
    
    employee_id = fields.Many2one('hr.employee',string=u'Employé')
    num_emp = fields.Char('Matricule', size=128)
    name_related = fields.Char('Nom', size=128)
    basic = fields.Float('Salaire de base')
    cnaps = fields.Float('CNAPS Travailleur')
    cnapsemp = fields.Float('CNAPS Employeur')
    brut = fields.Float('Salaire Brut')
    net = fields.Float('Salaire Net')
    date_from = fields.Date('Start Date')
    date_to = fields.Date('End Date')
    totalcnaps = fields.Float('TOTAL CNAPS')
    
    ref_employeur = fields.Char(u'Réf. Employeur')
    avantage = fields.Float('Avantage du mois')
    temps_presence = fields.Float('Temps presence')
    
#===============================================================================
#     def unlink(self, cr, uid, ids, context=None):
#         context = context or {}
#         if not context.get('forcer_suppresion'):
#             raise ValidationError("Supprimer le bulletin de paie lié pour une suppression")
# 
#         super(cnaps, self).unlink(cr, uid, ids, context=context)
#===============================================================================

