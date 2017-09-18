# -*- coding: utf-8 -*-

from odoo import fields, models, api
from odoo.exceptions import ValidationError

class GraduationType(models.Model):
    _name = "res.diplome"
    
    type = fields.Selection([
        ('bepc', 'Brevet d\'Etude du Premier Cycle'),
        ('bac', 'Baccalaureat'),
        ('licence', 'Licence'),
        ('master', 'Master'),
        ('doctorat', 'Doctorat')
    ], string='Diplôme')
    
    name = fields.Char(string='Nom', required=True)