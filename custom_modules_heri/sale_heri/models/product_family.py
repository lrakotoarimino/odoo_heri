# -*- coding: utf-8 -*-

from odoo import fields, models, api
from odoo.exceptions import ValidationError

class ProductFamily(models.Model):
    _name = "product.family"
    
    famille = fields.Char("Famille")
    reference = fields.Char("Référence")
    designation = fields.Char("Désignation")

class ProductTemplate(models.Model):
    _inherit = "product.template"
    
    product_family_id = fields.Many2one('product.family', string='Famille')