# -*- coding: utf-8 -*-

from odoo import fields, models, api
from odoo.exceptions import ValidationError
from docutils.nodes import reference

class ProductFamily(models.Model):
    _name = "product.family"
    
    famille = fields.Char("Famille")
    reference_family = fields.Char("Référence")
    name = fields.Char("Désignation")
class ProductHeri(models.Model):
    _inherit = "product.product"
    
    product_family_id = fields.Many2one('product.family', string='Famille')
    default_code=fields.Char("Ref", size=18,required=True)
    _sql_constraints = [
        ('default_code_unique', 'unique(default_code)', "A Reference already exists with this name . Reference's name must be unique!")
    ]

    