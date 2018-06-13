# -*- coding: utf-8 -*-

from odoo import fields, models
from odoo.exceptions import ValidationError

class ostie(models.Model):
    _name = "irsa"
    _description = "Etat irsa"
    
    employee_id = fields.Many2one('hr.employee',string=u'Employé', readonly=False)
    num_emp = fields.Char('Matricule', size=128, readonly=False)
    num_cin = fields.Char('CIN', size=128, readonly=False)
    name_related = fields.Char('Nom', size=128, readonly=False)
    basic = fields.Float('Salaire de base', readonly=False)
    irsa = fields.Float('IRSA', readonly=False)
    brut = fields.Float('Salaire Brut', readonly=False)
    net = fields.Float('Salaire Net', readonly=False)
    date_from = fields.Date('Start Date', readonly=False)
    date_to = fields.Date('End Date', readonly=False)
    avantage = fields.Float('Avantage du mois', readonly=False)
    
    #===========================================================================
    # def unlink(self, cr, uid, ids, context=None):
    #     context = context or {}
    #     if not context.get('forcer_suppresion'):
    #         raise ValidationError('Supprimer le bulletin de paie li� pour une suppression')
    #     
    #     super(ostie, self).unlink(cr, uid, ids, context=context)
    #==================================================================================
