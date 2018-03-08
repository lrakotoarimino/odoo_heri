# -*- coding: utf-8 -*-

from odoo import fields, models, api


class ResCurrency(models.Model):
    _inherit = 'res.currency'
    
    full_name = fields.Char(string='Full name')