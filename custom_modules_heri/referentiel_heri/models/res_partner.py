# -*- coding: utf-8 -*-

from odoo import fields, models, api
from odoo.exceptions import ValidationError

class CustomerSupplierHeri(models.Model):
    _inherit = "res.partner"
    
    prenom = fields.Char("Prénom", required=True)
    date_commencement = fields.Datetime('Date commencement', required=True, index=True, copy=False, default=fields.Datetime.now,\
        help="Date de debut d'occupation du poste.")
    date_fin = fields.Datetime('Date fin', required=True, index=True, copy=False, default=fields.Datetime.now,\
        help="Date de fin d'occupation du poste.")
    diplome_id = fields.Many2one('res.diplome', string='Diplôme')
    region_id = fields.Many2one('res.region', string='Région de résidence')
    formation = fields.Char("Formations", size=150)
    nbr_assistant = fields.Integer(string='Nombre d\'assistants', copy=False, default=0, size=3)
    cin = fields.Integer(string='CIN', copy=False, size=12)
    date_cin = fields.Date('Date délivrance CIN', default=fields.Date.today, required=True)
    cif = fields.Char(string='CIF')
    date_cif = fields.Date(default=fields.Date.today, string="Date CIF")
    nif = fields.Char("NIF", size=25)
    stat = fields.Char("STAT", size=25)
    emergency_call = fields.Char("Contact d'urgence", size=13)
    certificat_residence = fields.Char("Certificat de residence", size=50)
    certificat_existence = fields.Char("Certificat d'existence", size=50)