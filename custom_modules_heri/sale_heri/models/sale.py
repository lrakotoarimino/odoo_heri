# -*- coding: utf-8 -*-

from odoo import fields, models, api
from collections import namedtuple
from odoo.exceptions import UserError
from odoo.tools.float_utils import float_compare
import re

class SaleHeri(models.Model):
    _inherit = "sale.order"
    _description = "Facturation redevance mensuelle"
    
    kiosque_id = fields.Many2one('stock.location', string='Kiosque') 
    
#     @api.onchange('kiosque_id')
#     def onchange_ki