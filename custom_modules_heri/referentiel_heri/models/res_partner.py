# -*- coding: utf-8 -*-

from odoo import fields, models, api
from odoo.exceptions import ValidationError

class CustomerSupplierHeri(models.Model):
    _inherit = "res.partner"
    
    num = fields.Char("Ancien numéro")
    