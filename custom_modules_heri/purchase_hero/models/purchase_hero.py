# -*- coding: utf-8 -*-
from odoo import fields, models, api

    
class budgetRequest(models.Model):
    _name ="purchase.order"
    state=fields.Selection([
        ('draft', 'Budget Request'),
        ('valide', 'Validation'),
        ('debloc', 'Deblocage Cheque/OV'),
    ], string='Status',default='draft')
    def get_current_employee_id(self):
        employee_ids = self.env['hr.employee'].search([('user_id','=',self.env.uid)])
        if employee_ids:
            return employee_ids[0].id
        return False
    name = fields.Char("Reference Budget",required=True, index=True, copy=False, default='New')
    departement = fields.Many2one("hr.department",string="Departement Emetteur/section Analytique")
    partner_id = fields.Many2one("hr.employee",string="Fournisseur", default=get_current_employee_id)
    objet_demande =fields.Char("Objet de la demamnde",copy=False)
    sect_anal = fields.Char("Section Analytique d'imputation")
    nature_anal = fields.Char("Nature Analytique")
    observation = fields.Text("Observation")
    date_order=fields.Date("Date Budget Request",default=fields.Date.today)
    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code('budget.request.seq')
        return super(budgetRequest, self).create(vals)
    
