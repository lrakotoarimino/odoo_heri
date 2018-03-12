# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class BillingTable(models.Model):
    _name = "billing.table"
    
    name = fields.Char('Name')
    lines = fields.One2many('billing.table.line', 'table_id', string='Billing table lines')
    
 
class BillingTableLine(models.Model):
    _name = "billing.table.line"
    
    name = fields.Char('Name')
    table_id = fields.Many2one('billing.table', string='Billing table')
    month = fields.Selection([(1, 'January'), (2, 'February'), (3, 'March'), (4, 'April'),
                              (5, 'May'), (6, 'June'), (7, 'July'), (8, 'August'),
                              (9, 'September'), (10, 'October'), (11, 'November'), (12, 'December')])
    number_days = fields.Float(string='Number days')