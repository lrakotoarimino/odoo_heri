# -*- coding: utf-8 -*-

from odoo import fields, models, api
from odoo.exceptions import ValidationError

class Region(models.Model):
    _name = "res.region"
    
    region = fields.Char("Région", size=20, required=True)