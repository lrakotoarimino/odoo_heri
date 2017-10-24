# -*- coding: utf-8 -*-

from odoo import fields, models, api

class StockPicking(models.Model):
    _inherit = 'stock.picking' 
     
    bex_id = fields.Many2one('budget.expense.report')