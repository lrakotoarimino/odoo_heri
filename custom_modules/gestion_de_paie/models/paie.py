# -*- coding:utf-8 -*-

from odoo import api, fields, models, tools, _


class hr_contract(models.Model):
    _inherit = 'hr.contract'

    categorie = fields.Char('Categorie Professionnel', size=64)
    echellon = fields.Char('Echellon', size=64)
    indice = fields.Integer('Indice', size=10)
    horaire_hebdo = fields.Float('Horaire hebdomadaire')
    payment_mode = fields.Selection([('VIREMENT', 'VIREMENT'), ('ESPECE', 'ESPECE')], 'Mode de paiement')


class res_company(models.Model):
    _inherit = 'res.company'

    seuil_irsa = fields.Float('Seuil IRSA')
    taux_irsa = fields.Float('Taux IRSA')
    abat_irsa = fields.Float('Abattement IRSA')
    cotisation_cnaps_patr = fields.Float('Cotisation Patronale CNAPS')
    cotisation_cnaps_emp = fields.Float(u'Cotisation Employé CNAPS')
    plafond_cnaps = fields.Float('Plafond de la Securite Sociale')
    num_cnaps_patr = fields.Char(u'Numéro CNAPS', size=64)
    cotisation_sante_patr = fields.Float(u'Cotisation Patronale Santé')
    cotisation_sante_emp = fields.Float(u'Cotisation Employé Santé')
    org_sante = fields.Char('Organisme sanitaire', size=64)
    conge_mens = fields.Float(u'Nombre de jour congé  mensuel')
    
    siret = fields.Char('SIRET', size=64)
    ape = fields.Char('APE', size=64)
    

class hr_employee(models.Model):
    _inherit = 'hr.employee'
    
    num_cnaps_emp = fields.Char(u'Numéro CNAPS', size=64)
    num_emp = fields.Char(u'Numéro Matricule', size=64)
    num_cin = fields.Char(u'Numéro CIN', size=64)
    

class HrPayslip(models.Model):
    _inherit = 'hr.payslip'
    
    def get_avance_salaire(self):
        advance_obj = self.env['hr.wage.advance']
        advances = advance_obj.search(['&', '&', '&', ('employee_id', '=', self.employee_id.id), ('state', '=', 'ok'), ('date', '>=', self.date_from), ('date', '<=', self.date_to)])
        total_advance = 0.0
        for advance in advances:
            total_advance += advance.amount
        return total_advance
    
    #Redefinition fonction onchange_employee()
    
    @api.onchange('employee_id', 'date_from')
    def onchange_employee(self):
        res = super(HrPayslip, self).onchange_employee()
        
        if (not self.employee_id) or (not self.date_from) or (not self.date_to):
            return
        
        worked_days_data_list = [
                 {'code': 'HS2', 'contract_id': self.contract_id.id, 'name': u'Heure supplémentaire 2'},
                 {'code': 'HMNUIT', 'contract_id': self.contract_id.id, 'name': u'Heure majoré nuit'},
                 {'code': 'HMDIM', 'contract_id': self.contract_id.id, 'name': u'Heure majoré dimanche'},
                 {'code': 'HMJF', 'contract_id': self.contract_id.id, 'name': u'Heure majoré jour férié'}]
                 
        worked_days_lines = self.worked_days_line_ids.browse([])
        for worked_days_data in worked_days_data_list:
            self.worked_days_line_ids += worked_days_lines.new(worked_days_data)
        
        input_data_list = [
                 
                 # {'code': 'AVANCE15', 'contract_id': self.contract_id.id, 'amount': self.get_avance_salaire(), 'name': 'Avance quinzaine'},
                 {'code': 'AVANCE15', 'contract_id': self.contract_id.id, 'name': 'Avance quinzaine'},
                 {'code': 'AVANCESP', 'contract_id': self.contract_id.id, 'name': u'Avance spécial'},
                 {'code': 'PRM', 'contract_id': self.contract_id.id, 'name': 'Prime'},
                 {'code': 'AUTRES', 'contract_id': self.contract_id.id, 'name': 'Autres retenues'}]
        
        input_lines = self.input_line_ids.browse([])
        for input_data in input_data_list:
            self.input_line_ids += input_lines.new(input_data)
    
        return
    
    etat_salaire_id = fields.Many2one('etat.salaire', string='Etat salaire')
    ostie_id = fields.Many2one('ostie', string='Etat OSTIE')
    irsa_id = fields.Many2one('irsa', string='Etat IRSA')
    cnaps_id = fields.Many2one('cnaps', string='Etat CNAPS')
    
    @api.model
    def create(self, vals):
        
        payslip_id = super(HrPayslip, self).create(vals)
        payslip_obj = self.env['hr.payslip']
        data = payslip_obj.browse([payslip_id.id])
        vals = {
            'employee_id': data.employee_id.id,
            'num_emp': data.employee_id.num_emp,
            'num_cin': data.employee_id.num_cin,
            'name_related': data.employee_id.name,
            'date_from': data.date_from,
            'date_to': data.date_to,
            }
        etat_id = self.env['etat.salaire'].create(vals).id
        ostie_id = self.env['ostie'].create(vals).id
        irsa_id = self.env['irsa'].create(vals).id
        cnaps_id = self.env['cnaps'].create(vals).id
        
        payslip_obj.browse(payslip_id.id).write({
                   'etat_salaire_id': etat_id,
                   'ostie_id': ostie_id,
                   'irsa_id': irsa_id,
                   'cnaps_id': cnaps_id})
        return payslip_id
        
    @api.multi
    def write(self, values):
        result = super(HrPayslip, self).write(values)
        data = self.browse(self.id)
        if not (data.etat_salaire_id and data.ostie_id and data.cnaps_id and data.irsa_id):
            return result
        vals = {
            'employee_id': data.employee_id.id,
            'num_emp': data.employee_id.num_emp,
            'num_cin': data.employee_id.num_cin,
            'name_related': data.employee_id.name,
            'date_from': data.date_from,
            'date_to': data.date_to,
            }
        for line in data.line_ids:
            if line.code == 'BASIC':
                vals['basic'] = line.total 
            if line.code == 'OMSI_EMP': 
                vals['omsi'] = line.total
            if line.code == 'CNAPS_EMP':
                vals['cnaps'] = line.total
            if line.code == 'GROSS':
                vals['brut'] = line.total
            if line.code == 'IRSA':
                vals['irsa'] = line.total
             
        #for line in data.details_by_salary_rule_category:
            if line.code == 'OMSI_PAT':
                vals['omsiemp'] = line.total
            if line.code == 'CNAPS_PAT':
                vals['cnapsemp'] = line.total
            if line.code == 'NET':
                vals['net'] = line.total
                 
        vals['totalomsi'] = vals.get('omsi', 0.0) + vals.get('omsiemp', 0.0)
        vals['totalcnaps'] = vals.get('cnaps', 0.0) + vals.get('cnapsemp', 0.0)
        #etat_salaire
        etat = self.env['etat.salaire'].browse(data.etat_salaire_id.id)
        etat.write(vals)
         
        #ostie
        vals_ostie = vals.copy()
        not_in_ostie = ['cnaps', 'cnapsemp', 'totalcnaps', 'irsa']
        for cle in not_in_ostie:
            if cle in vals_ostie:
                del vals_ostie[cle]
        
        ostie = self.env['ostie'].browse(data.ostie_id.id)
        ostie.write(vals_ostie)
          
        #irsa
        vals_irsa = vals.copy()
        not_in_irsa = ['cnaps', 'cnapsemp', 'totalcnaps', 'omsi', 'omsiemp', 'totalomsi']
        for cle in not_in_irsa:
            if cle in vals_irsa:
                del vals_irsa[cle]
        irsa = self.env['irsa'].browse(data.irsa_id.id)
        irsa.write(vals_irsa)
          
        #cnaps
        vals_cnaps = vals.copy()
        not_in_cnaps = ['irsa', 'omsi', 'omsiemp', 'totalomsi']
        for cle in not_in_cnaps:
            if cle in vals_cnaps:
                del vals_cnaps[cle]
        cnaps = self.env['cnaps'].browse(data.cnaps_id.id)
        cnaps.write(vals_cnaps)
                 
        return result
     
    #===========================================================================
    # def unlink(self, cr, uid, ids, context=None):
    #     context['forcer_suppresion'] = True
    #     for data in self.browse(cr, uid, ids, context=context):
    #         self.pool.get('etat.salaire2').unlink(cr, uid, [data.etat_salaire_id.id], context=context)
    #         self.pool.get('ostie').unlink(cr, uid, [data.ostie_id.id], context=context)
    #         self.pool.get('irsa2').unlink(cr, uid, [data.irsa_id.id], context=context)
    #         self.pool.get('cnaps2').unlink(cr, uid, [data.cnaps_id.id], context=context)
    #     super(hr_payslip, self).unlink(cr, uid, ids, context=context)
    #===========================================================================
