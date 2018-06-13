# -*- coding: utf-8 -*-

from odoo import fields, models
from odoo.exceptions import ValidationError

class ostie(models.Model):
    _name = "ostie"
    _description = "Etat ostie"
    
    employee_id = fields.Many2one('hr.employee',string=u'Employé')
    num_emp = fields.Char('Matricule', size=128)
    num_cin = fields.Char('CIN', size=128)
    name_related = fields.Char('Nom', size=128)
    basic = fields.Float('Salaire de base')
    omsi = fields.Float('OSTIE Travailleur')
    omsiemp = fields.Float('OSTIE Employeur')
    brut = fields.Float('Salaire Brut')
    net = fields.Float('Salaire Net')
    date_from = fields.Date('Start Date')
    date_to = fields.Date('End Date')
    totalomsi = fields.Float('TOTAL OMSI')
    
    avantage = fields.Float('Avantage du mois')
    temps_presence = fields.Float('Temps presence')
    
    #===========================================================================
    # def unlink(self, cr, uid, ids, context=None):
    #     context = context or {}
    #     if not context.get('forcer_suppresion'):
    #         raise ValidationError( 'Supprimer le bulletin de paie lié pour une suppression')
    #     
    #     super(ostie, self).unlink(cr, uid, ids, context=context)
    #===========================================================================