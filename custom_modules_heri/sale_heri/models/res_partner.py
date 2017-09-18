# -*- coding: utf-8 -*-

from odoo import fields, models, api
from odoo.exceptions import ValidationError

class CustomerHeri(models.Model):
    _inherit = "res.partner"
    
    prenom = fields.Char("Prénom", required=True)
    date_commencement = fields.Datetime('Date commencement', required=True, index=True, copy=False, default=fields.Datetime.now,\
        help="Date de debut d'occupation du poste.")
    date_fin = fields.Datetime('Date fin', required=True, index=True, copy=False, default=fields.Datetime.now,\
        help="Date de fin d'occupation du poste.")
    diplome_id = fields.Many2one('res.diplome', string='Diplôme')
    region_id = fields.Many2one('res.region', string='Région de résidence')
    formation = fields.Char("Formations")
    nbr_assistant = fields.Integer(string='Nombre d\'assistants', copy=False, default=0)
    cin = fields.Integer(string='CIN', copy=False, default=0)
    emergency_call = fields.Char("Contact d'urgence")
    nif = fields.Char("NIF")
    stat = fields.Char("STAT")
    certificat_residence = fields.Char("Certificat de residence")
    certificat_existence = fields.Char("Certificat d'existence")