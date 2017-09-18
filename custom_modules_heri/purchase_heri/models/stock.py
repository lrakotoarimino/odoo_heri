# -*- coding: utf-8 -*-

from odoo import fields, models, api

class StockPicking(models.Model):
    _inherit = "stock.picking"
    
    #champs du Budget Expense Report
    department_id = fields.Many2one('hr.department', string='Département émetteur/Section analytique', )
    objet = fields.Text("Objet de la demande")
    section = fields.Char("Section analytique d’imputation")
    nature = fields.Char("Nature analytique")
    budgetise = fields.Char("Budgetisé :")
    cumul = fields.Char("Cumul Real. + ENgag. :")

class StockPackOperation(models.Model):
    _inherit = "stock.pack.operation"
    
    prix_unitaire = fields.Float('PU')
    montant_br = fields.Float('Montant BReq', readonly=True)
    montant_realise = fields.Float(compute='_compute_amount', string='Montant Réalisé', readonly=True, store=True)
    taxes_id = fields.Many2many('account.tax', string='Taxes', domain=['|', ('active', '=', False), ('active', '=', True)])
    
    @api.depends('qty_done', 'prix_unitaire')
    def _compute_amount(self):
        
        cur = self.env['res.currency'].search([('id','=',105)], limit=1)
        part = self.env['res.partner'].search([('id','=',13)], limit=1)
        for line in self:
            taxes = line.taxes_id.compute_all(line.prix_unitaire, cur, line.qty_done, product=line.product_id, partner=part)
            line.update({
#                 'price_tax': taxes['total_included'] - taxes['total_excluded'],
#                 'price_total': taxes['total_included'],
                'montant_realise': taxes['total_excluded'],
            })
