# -*- coding: utf-8 -*-

from odoo import fields, models


class ProductHeri(models.Model):
    _inherit = "product.product"
    
    rental_price = fields.Float(string='Rental price')