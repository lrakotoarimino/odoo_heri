# -*- coding: utf-8 -*-

from odoo import fields, models, api
from odoo.fields import Char

class CodeBudgetaireRegion(models.Model):
    _name = "br.region"
    
    region = fields.Char("Région")

class PurchaseHeri(models.Model):
    _inherit = "purchase.order"
    
    def get_department_id(self):
        employee_obj = self.env['hr.employee']
        #on cherche l'id de l'employe en cours dans la base hr_employee
        employee_id = employee_obj.search([('user_id','=',self.env.uid)])
        #si employee_id n'est pas vide
        if employee_id:
            #get id du departement
            return employee_id[0].department_id.id
        return False
    
    def get_employee_id(self):
        employee_id = self.env['hr.employee'].search([('user_id','=',self.env.uid)])
        if employee_id:
            return employee_id[0].id
        return False
    
    def get_manager_id(self):
        employee_id = self.env['hr.employee'].search([('user_id','=',self.env.uid)])
        if employee_id:
            return employee_id[0].parent_id.id
        return False
    
    state = fields.Selection([
        ('nouveau', 'nouveau'),
        ('a_approuver', 'A approuver'),
        ('non_prevue', 'Non prévue'),
        ('attente_validation', 'Attente de validation'),
        ('purchase', 'Validé'),
        ('refuse', 'Refusé'),
        ('done', 'Terminé'),
        ('cancel', 'Annulé')
        ], string='Etat', readonly=True, default='nouveau', track_visibility='onchange')
    
    department_id = fields.Many2one('hr.department', string='Département émetteur/Section analytique', default=get_department_id)
    objet = fields.Text("Objet de la demande")
    employee_id = fields.Many2one('hr.employee', string='Demandeur', default=get_employee_id)
    manager_id = fields.Many2one('hr.employee', string='Responsable d\'approbation',default=get_manager_id)
    description = fields.Char("Description")
    region_id = fields.Many2one('br.region', string='Région')
    is_manager = fields.Boolean(compute="_get_is_manager", string='Est un manager')
    section = fields.Char("Section analytique d’imputation")
    nature = fields.Char("Nature analytique")
    budgetise = fields.Char("Budgetisé :")
    cumul = fields.Char("Cumul Real. + ENgag. :")
    
#     type_purchase = fields.Char('test')
#     type_purchase_import = fields.Char('test')
    
    @api.one
    def _get_is_manager(self):
        self.is_manager = False
        current_employee_id = self.env['hr.employee'].search([('user_id','=',self.env.uid)]).id
        manager_id = self.employee_id.department_id.manager_id.id
        if current_employee_id == manager_id:
            self.is_manager = True
            
    
    def action_a_approuver(self):
        self.write({'state':'a_approuver'})
    def action_non_prevu(self):
        self.write({'state':'non_prevue'})
    def action_refus_finance(self):
        self.write({'state':'refuse'})
    def action_attente_validation(self):
        self.write({'state':'attente_validation'})
    def action_refus_dg(self):
        self.write({'state':'refuse'})
    def action_confirmed(self):
        self.write({'state': 'purchase'})
        self._create_picking()
    