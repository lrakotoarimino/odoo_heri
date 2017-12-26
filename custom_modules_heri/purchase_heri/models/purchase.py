# -*- coding: utf-8 -*-

from odoo import fields, models, api
from odoo.exceptions import UserError
from odoo.tools import float_compare, float_round
from collections import namedtuple
from odoo.api import onchange
from datetime import datetime
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT

#Region
class ResRegion(models.Model):
    _name = "res.region"
    
    name = fields.Char(u'Région')
    frais_base = fields.Float("Frais de base")
    
#Budget Request Achat
class PurchaseHeri(models.Model):
    _inherit = "purchase.order"
    _description = "Budget Request"
    
    @api.depends('taux_change', 'amount_untaxed')
    def _compute_amount_ht_ariary(self):
        for order in self:
            order.amount_total_ariary = order.taux_change * order.amount_untaxed
            
    amount_total_ariary = fields.Float(string='Montant HT (Ar)', compute='_compute_amount_ht_ariary')
    
    def _prepare_order_line_from_po_line(self, line):
        vals = {
                'product_id': line.product_id,
                'name': line.product_id.name,
                'designation_frns': 'Droit de douane %s' % (line.product_id.name),
                'product_qty': 1.0,
                'product_uom': line.product_uom,
                'price_unit': 0.0, 
                'order_id': self.id,
                'purchase_line_id': line.id,
                'date_planned': datetime.today().strftime(DEFAULT_SERVER_DATETIME_FORMAT),
                }
        return vals
        
    @api.onchange('parents_ids')
    def onchange_parents_ids(self):
        if self.service_type != 'douane':
            return {}
        new_lines = self.env['purchase.order.line']
        for line in self.parents_ids.order_line:
            data = self._prepare_order_line_from_po_line(line)
            new_line = new_lines.new(data)
            new_lines += new_line

        self.order_line = new_lines
        return {}
    
    @api.onchange('parent_id')
    def onchange_parent_id(self):
        new_lines = self.env['purchase.order.line']
        self.partner_id = self.parent_id.partner_id
        self.partner_ref = self.parent_id.partner_ref
        self.nature = self.parent_id.nature
        self.currency_id = self.parent_id.currency_id
        self.taux_change = self.parent_id.taux_change
        self.objet = self.parent_id.objet
        self.section = self.parent_id.section
        for line in self.parent_id.order_line:
            data = self._prepare_order_line_from_po_line(line)
            data['price_unit'] = line.price_unit
            data['product_qty'] = line.product_qty
            data['designation_frns'] = line.product_id.name
            data['taxes_id'] = line.taxes_id
            data['discount'] = line.discount
            new_line = new_lines.new(data)
            new_lines += new_line

        self.order_line = new_lines
        return {}
    
    @api.model
    def create(self, values):
        order = super(PurchaseHeri,self).create(values)
        if not values.get('is_breq_id_sale',False):
            #S'il ne provient pas d'un BCI dans la facturation des materiels en mauvais etat
            if not values.get('order_line',False) and not values.get('is_from_bci',False):
                raise UserError('Veuillez renseigner les lignes de la commande.')
        return order 
    
    @api.model
    def _prepare_picking(self):
        res = super(PurchaseHeri,self)._prepare_picking()
        
        #Modifier type de preparation
        if self.is_breq_stock :
            if not picking_type_id.default_location_dest_id:
                raise UserError("Le type de préparation du champ 'Livré à' %s n'a pas d'Emplacement de destination par défaut. Merci de configurer" % (self.picking_type_id.name))

            res['picking_type_id'] = self.picking_type_id.id
            #res['location_dest_id'] = self.env.ref('purchase_heri.stock_location_virtual_heri').id
            res['location_dest_id'] = self.picking_type_id.default_location_dest_id.id
            res['location_id'] = self.location_id.id
            res['move_type'] = 'direct'
            res['employee_id'] = self.employee_id.id
            res['breq_id'] = self.id
            res['amount_untaxed'] = self.amount_untaxed
            res['is_bs'] = True
            res['mouvement_type'] = self.mouvement_type
        
        return res
    #creation bon de sortie (budget request stock)
    @api.multi
    def _create_picking2(self):
        picking_obj = self.env['stock.picking']
        
        for order in self:
            picking_type_id = order.env.ref('purchase_heri.type_preparation_heri')
            picking_type_id.write({'default_location_src_id': order.location_id.id})
            
            self._prepare_picking()
            vals = {
                    'picking_type_id': picking_type_id.id,
                    'partner_id': order.partner_id.id,
                    'date': order.date_order,
                    'origin': order.name,
                    'location_dest_id': order.env.ref('purchase_heri.stock_location_virtual_heri').id,
                    'location_id': order.location_id.id,
                    'company_id': order.company_id.id,
                    'move_type': 'direct',
                    'employee_id': order.employee_id.id,
                    'breq_id': order.id,
                    'section': order.section,
                    'amount_untaxed': order.amount_untaxed,
                    'is_bs': True,
                    'mouvement_type': order.mouvement_type,
                    }
            picking_id = picking_obj.create(vals)
            move_lines = order.order_line._create_stock_moves(picking_id)
            if not move_lines:
                raise UserError('Mouvement de stock non créé')
            move_lines = move_lines.filtered(lambda x: x.state not in ('done', 'cancel')).action_confirm()
            move_lines.action_assign()

        return True
    
    def action_cancel(self):
        picking_obj = self.env['stock.picking']
        picking_id = picking_obj.search([('breq_id','=',self.id)],limit=1)
        picking_id.mapped('move_lines').action_cancel()
    
    #creation budget expense report (budget request achat)
    @api.multi
    def _create_bex(self):
        bex_obj = self.env['budget.expense.report']
        attachment_obj = self.env['ir.attachment']
        
        for order in self:
            attachment_ids = attachment_obj.search([('res_model','=','purchase.order'),('res_id','=',order.id)])
            len_attachment = len(attachment_ids)
            if order.purchase_type == 'purchase_import':
                if len_attachment < 1:
                    raise UserError("Veuillez d'abord insérer une pièce jointe dans le document.")
            elif order.purchase_type in ('purchase_stored', 'purchase_stored'):
                if len_attachment < 3:
                    raise UserError("Veuillez d'abord insérer au moins trois (3) pièces jointes dans le document.")
                
            vals = {
#                     'partner_id': order.partner_id.id,
                    'origin': order.name,
#                     'department_id': order.department_id.id,
#                     'objet': order.objet,
#                     'section': order.section,
#                     'nature': order.nature,
                    'budgetise': order.budgetise,
                    'cumul': order.cumul,
                    'solde_rembourser': order.solde,
#                     'currency_id': order.currency_id.id,
#                     'employee_id': order.employee_id.id,
#                     'manager_id': order.manager_id.id,
                    'journal_id':order.journal_id.id,
                    'amount_untaxed_breq': order.amount_untaxed,
                    'amount_tax_breq': order.amount_tax,
                    'amount_total_breq': order.amount_total,
                    'breq_id': order.id,
#                     'purchase_type': order.purchase_type,
                    
                    'company_id': order.company_id.id,
                    'location_id': order.partner_id.property_stock_supplier.id,
                    'location_dest_id': order._get_destination_location(),
                    'picking_type_id': order.picking_type_id.id,
                    'group_id': order.group_id.id, 
                    'move_type': 'direct',
                    }
            bex = bex_obj.create(vals)
            bex_lines = order.order_line._create_bex_lines(bex)
            
        return True
    

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
    
    @api.depends('state','statut_bex')
    def _concate_state(self):
        for res in self:
            etat_bex = ""
            bx=""
            if res.statut_bex:
                etat_bex = res.statut_bex
                bx += dict(res.env['budget.expense.report'].fields_get(allfields=['state'])['state']['selection'])[etat_bex]
            br = dict(res.env['purchase.order'].fields_get(allfields=['state'])['state']['selection'])[res.state]
            
            res.statut_breq_bex = br + " / " + bx
           
    is_breq_id_sale = fields.Boolean('Est un breq stock sale') 
    is_breq_stock = fields.Boolean('Est un budget request stock', default=False)
    statut_breq_bex = fields.Char(compute="_concate_state", string='Etat BReq/BEX')
    is_from_bci = fields.Boolean('Est-il venu d\'un bci lors de la facturation de materiel en mauvais etat dans vente', default=False)
    
    justificatif = fields.Text("Justificatif Non prévu/Dépassement")
    state = fields.Selection([
        ('nouveau', 'Nouveau'),
        ('confirmation_dg', 'En attente validation DG'),
        ('a_approuver', 'Avis supérieur hiérarchique'),
        ('aviser_finance', 'Etablissement OV'),
        ('ov_to_bank', 'OV envoyé à la banque'),
        ('br_lie', 'Attente pièce jointe'),
        ('calcul_pr', 'Prix de revient calculé'),
        ('non_prevue', 'En vérification compta'),
        ('attente_validation', 'En attente validation DG'),
        ('wait_mode', 'En attente paiement finance'),
        ('mode_de_paiment_valide', 'Mode de paiement Validé'),
        ('purchase', 'BEX'),
        ('refuse', 'Refusé'),
        ('done', 'Terminé'),
        ('bs', 'Bon de sortie'),
        ('cancel', 'Annulé'),
        ], string='Etat BReq', readonly=True, default='nouveau', track_visibility='onchange')
    
    purchase_type = fields.Selection([
        ('purchase_stored', 'Achats locaux stockés'),
        ('purchase_not_stored', 'Achats locaux non stockés'),
        ('purchase_import', 'Achats à l\'importation'),
    ], string='Type d\'achat')
    
    service_type = fields.Selection([
        ('transport', 'Transport'),
        ('assurance', 'Assurance'),
        ('douane', 'Droit de douane'),
        ('additionel','Additionel'),
        ('fille','Fille'),
    ], string='Type de service')
    
    purchase_import_type = fields.Selection([
        ('purchase_import_stored', 'Achats à l\'import stockés'),
        ('purchase_import_not_stored', 'Achats à l\'import non stockés')
    ], string='Type d\'achat',track_visibility='onchange')
    
    import_type = fields.Many2one('purchase.import.type',string="Type Import")
        
    department_id = fields.Many2one('hr.department', string='Département émetteur', default=get_department_id, readonly=True)
    objet = fields.Text("Objet de la demande")
    employee_id = fields.Many2one('hr.employee', string='Demandeur', default=get_employee_id, readonly=True)
    manager_id = fields.Many2one('hr.employee', string='Responsable d\'approbation',default=get_manager_id, readonly=True)
    description = fields.Char("Description")
    region_id = fields.Many2one('res.region', string='Région')
    is_manager = fields.Boolean(compute="_get_is_manager", string='Est un manager')
    change_state_date = fields.Datetime(string="Date changement d\'état", readonly=True, help="Date du dernier changement d\'état.") 
    purchase_ids = fields.One2many('purchase.order', string="purchase_ids", compute='_compute_br_lie')
    br_lie_count = fields.Integer(compute='_compute_br_lie')
    purchase_fille_ids = fields.One2many('purchase.order', string="purchase_fille_ids", compute='_compute_breq_fille')
    breq_fille_count = fields.Integer(compute='_compute_breq_fille')
    purchase_ids_transport = fields.One2many('purchase.order', string="purchase_ids_transport", compute='_compute_br_transport_lie')
    br_transport_lie_count = fields.Integer(compute='_compute_br_transport_lie')
    taux_change = fields.Float(string='Taux de change')
    
    purchase_ids_douane = fields.One2many('purchase.order', string="purchase_ids_douane", compute='_compute_br_douane_lie')
    br_douane_lie_count = fields.Integer(compute='_compute_br_douane_lie')
    
    purchase_ids_assurance = fields.One2many('purchase.order', string="purchase_ids_assurance", compute='_compute_br_assurance_lie')
    br_assurance_lie_count = fields.Integer(compute='_compute_br_assurance_lie')
    
    parent_id = fields.Many2one('purchase.order',readonly=True, string='BReq mère')
    parents_ids = fields.Many2one('purchase.order',readonly=True, string='BReq d\'origine')
    date_prevu = fields.Datetime(string="Date prévue livraison", default=fields.Datetime.now())
    modalite_paiement = fields.Float(string='Modalité de paiement')
    location_id = fields.Many2one('stock.location', string='Magasin Origine') 
     
    section = fields.Char("Section analytique d’imputation")
    nature = fields.Char("Nature analytique")
    budgetise = fields.Float("Budgetisé")
    cumul = fields.Float("Cumul Real. + Engag.")
    solde = fields.Float("Solde de budget")
    statut_budget = fields.Selection(compute="_get_statut_budget", string="Statut", 
                         selection=[('prevu','PREVU'),
                                    ('non_prevu','NON PREVU'),
                                    ('depasse','DEPASSEMENT')], store=True, default='prevu')
    
    journal_id = fields.Many2one('account.journal', string='Mode de paiement', domain=[('type', 'in', ('bank', 'cash'))])
    is_creator = fields.Boolean(compute="_get_is_creator", string='Est le demandeur')
    
    statut_bex = fields.Selection(compute="_get_statut_bex", string='Etat BEX',
                      selection=[
                             ('draft', 'Nouveau'), ('cancel', 'Cancelled'),
                             ('attente_hierarchie','Avis supérieur hierarchique'),
                             ('hierarchie_ok','Validation supérieur hierarchique'), 
                             ('comptabilise','Comptabilisé')])
    mouvement_type = fields.Selection([
        ('bs', 'bon de sortie'),
        ('be', u'bon d entrée'),
        ('bci', 'Bon de cession Interne'),
        ('br', 'Bon de Retour'),
        ], string='Type de Mouvement', readonly=True, track_visibility='onchange')
    
    bex_lie_count = fields.Integer(compute='_compute_bex_lie')
    bex_id = fields.One2many('budget.expense.report', string="bex_ids", compute='_compute_bex_lie')

    picking_ids_bs = fields.One2many('stock.picking', string="purchase_ids", compute='_compute_bs_lie')
    picking_bci_id = fields.Many2one('stock.picking', string="purchase_ids")
    bs_lie_count = fields.Integer(compute='_compute_bs_lie')
    all_bex_validated = fields.Boolean('Tout bex est Comptabilisé',compute='_compute_all_validated')   
    bs_id = fields.Many2one('stock.picking', string="Bon de sortie lié", compute='_compute_bs_lie')
    
    @api.model
    def _get_currency_en_ar(self):
        return self.env.ref('base.MGA').id
          
    currency_en_ar = fields.Many2one('res.currency', default=_get_currency_en_ar, readonly=True)
    
    @api.depends('statut_bex')
    def _compute_all_validated(self):
        for order in self:
            current_brq_id = self.env['purchase.order'].search([('parents_ids','=',order.id),('service_type','=','transport')])
            if current_brq_id and all([x.statut_bex == 'comptabilise' for x in current_brq_id]) :
                order.all_bex_validated = True
            else :
                order.all_bex_validated = False
                
        
    @api.onchange('location_id')
    def onchange_location_id(self):
        if not self.is_breq_stock:
            return
        for line in self.order_line:
            line.unlink()
    
    @api.onchange('purchase_type')
    def onchange_purchase_type(self):
        if self.parents_ids and self.purchase_type == 'purchase_import':
            return {
                    'warning': {
                                'title': 'Avertissement!', 'message': 'Vous ne pouvez pas choisir l\'Achat à l\'importation pour un Budget Request Additionnel.'
                            },
                    'value': {
                              'purchase_type': False,
                            }
                    }
            
    @api.onchange('budgetise', 'cumul')
    def onchange_budget_cumul(self):
        self.solde = self.budgetise-self.cumul       
    
    @api.onchange('partner_id', 'company_id')
    def onchange_partner_id(self):
        if not self.partner_id:
            self.fiscal_position_id = False
            self.payment_term_id = False
            
            #Redefintion
            if self.purchase_type == 'purchase_import':
                self.currency_id = self.env.ref('base.EUR').id
            else: 
                self.currency_id = self.env.ref('base.MGA').id
            #Fin redefinition
        else:
            self.fiscal_position_id = self.env['account.fiscal.position'].with_context(company_id=self.company_id.id).get_fiscal_position(self.partner_id.id)
            self.payment_term_id = self.partner_id.property_supplier_payment_term_id.id
            
            #Redefintion
            if self.partner_id.property_purchase_currency_id:
                self.currency_id =  self.partner_id.property_purchase_currency_id.id
            #Fin redefinition
        return {}
      
    @api.multi
    def action_bs_lie(self):
        action = self.env.ref('stock_heri.action_bon_de_sortie_lie')
        result = action.read()[0]
        return result
    
    @api.multi
    def _compute_bs_lie(self):
        for order in self:
            bs_child_purchase = self.env['stock.picking'].search([('breq_id','=',order.id),('mouvement_type','=','bs')],limit=1)
            if bs_child_purchase:
                order.picking_ids_bs = bs_child_purchase
                order.bs_lie_count = len(bs_child_purchase)
                order.bs_id = bs_child_purchase.id
                
    @api.multi
    def _compute_bex_lie(self):
        for bx in self:
            bex_child_purchase = self.env['budget.expense.report'].search([('breq_id','=',bx.id)])
            if bex_child_purchase:
                bx.bex_id = bex_child_purchase
                bx.bex_lie_count = len(bex_child_purchase)
    
    @api.multi
    def action_view_bex(self):
        action = self.env.ref('purchase_heri.action_bex_lie_tree')
        result = action.read()[0]
        return result
        
    @api.one
    def _get_statut_bex(self):
        bex_lie = self.env['budget.expense.report'].search([('breq_id','=',self.id)], limit=1)
        if bex_lie:
            self.statut_bex = bex_lie.state
            
    @api.one
    def _get_is_creator(self):
        self.is_creator = False
        current_employee_id = self.env['hr.employee'].search([('user_id','=',self.env.uid)], limit=1).id
        employee_id = self.employee_id.id
        if current_employee_id == employee_id:
            self.is_creator = True
              
    @api.multi
    def _compute_br_lie(self):
        for br in self:
            purchase_child = self.env['purchase.order'].search([('parents_ids','=',br.id),('service_type','=','additionel')])
            if purchase_child:
                br.purchase_ids = purchase_child
                br.br_lie_count = len(purchase_child)
             
    @api.multi
    def _compute_breq_fille(self):
        for breq in self:
            purchase_child = self.env['purchase.order'].search([('parent_id','=',breq.id),('service_type','=','fille')])
            if purchase_child:
                breq.purchase_fille_ids = purchase_child
                breq.breq_fille_count = len(purchase_child)
       
    @api.multi
    def _compute_br_transport_lie(self):
        for br_transport in self:
            purchase_child_transport = self.env['purchase.order'].search([('parents_ids','=',br_transport.id),('service_type','=','transport')])
            if purchase_child_transport:
                br_transport.purchase_ids_transport = purchase_child_transport
                br_transport.br_transport_lie_count = len(purchase_child_transport)
    
    @api.multi
    def _compute_br_douane_lie(self):
        for br_transport in self:
            purchase_child_douane = self.env['purchase.order'].search([('parents_ids','=',br_transport.id),('service_type','=','douane')])
            if purchase_child_douane:
                br_transport.purchase_ids_douane = purchase_child_douane
                br_transport.br_douane_lie_count = len(purchase_child_douane)
    
    @api.multi
    def _compute_br_assurance_lie(self):
        for br_transport in self:
            purchase_child_assurance = self.env['purchase.order'].search([('parents_ids','=',br_transport.id),('service_type','=','assurance')])
            if purchase_child_assurance:
                br_transport.purchase_ids_assurance = purchase_child_assurance
                br_transport.br_assurance_lie_count = len(purchase_child_assurance)
                
    @api.multi
    def action_view_br_lie(self):
        action = self.env.ref('purchase_heri.action_br_lie_tree')
        result = action.read()[0]
        return result
    
    @api.multi
    def action_view_breq_fille(self):
        action = self.env.ref('purchase_heri.action_breq_fille')
        result = action.read()[0]
        return result
    
    @api.multi
    def action_view_br_transport(self):
        action = self.env.ref('purchase_heri.action_br_achat_import_transport')
        result = action.read()[0]
        return result
    
    @api.multi
    def action_view_br_douane(self):
        action = self.env.ref('purchase_heri.action_br_achat_import_douane')
        result = action.read()[0]
        return result
    
    @api.multi
    def action_view_br_assurance(self):
        action = self.env.ref('purchase_heri.action_br_achat_import_assurance')
        result = action.read()[0]
        return result
    
    @api.depends('solde','budgetise','order_line')
    def _get_statut_budget(self):
        for breq in self:
            if self.purchase_type != 'purchase_import':
                if breq.budgetise > 0.0 and breq.solde > 0.0:
                    if breq.amount_total > breq.solde:
                        breq.statut_budget = 'depasse'
                    else:
                        breq.statut_budget = 'prevu'
                if breq.budgetise == 0.0 and breq.solde < 0.0:
                    breq.statut_budget = 'non_prevu'
                if breq.budgetise > 0.0 and breq.solde <= 0.0 :
                    breq.statut_budget = 'depasse'
                if breq.budgetise == 0.0 and breq.solde == 0.0:
                    breq.statut_budget = 'non_prevu'
            else:
                breq.statut_budget = 'prevu'
            
    @api.one
    def _get_is_manager(self):
        self.is_manager = False
        current_employee_id = self.env['hr.employee'].search([('user_id','=',self.env.uid)]).id
        manager_id = self.employee_id.parent_id.id
        if current_employee_id == manager_id:
            self.is_manager = True
            
    def action_a_approuver(self):
        self.write({'state':'a_approuver', 'change_state_date': fields.Datetime.now()})
    def action_refus_superieur(self):
        self.write({'state':'nouveau', 'change_state_date': fields.Datetime.now()})
        self.action_cancel()
    def action_refus_dg_import(self):
        self.write({'state':'nouveau', 'change_state_date': fields.Datetime.now()})
    def action_non_prevu(self):
        self.write({'state':'non_prevue', 'change_state_date': fields.Datetime.now()})
    def action_refus_finance(self):
        self.write({'state':'refuse', 'change_state_date': fields.Datetime.now()})
    def action_attente_validation(self):
        self.write({'state':'attente_validation', 'change_state_date': fields.Datetime.now()})
    def action_attente_validation_import(self):
        self.write({'state':'confirmation_dg', 'change_state_date': fields.Datetime.now()})
    def action_refus_dg(self):
        self.write({'state':'refuse', 'change_state_date': fields.Datetime.now()})
    def action_wait_mode(self):
        self.write({'state': 'wait_mode', 'change_state_date': fields.Datetime.now()})
    def action_confirmed(self):
        self.write({'state': 'purchase', 'change_state_date': fields.Datetime.now()})
        self._create_bex()
    def action_annuler(self):
        self.write({'state': 'cancel', 'change_state_date': fields.Datetime.now()})
    def action_paiement_valider(self):
        self.write({'state': 'mode_de_paiment_valide', 'change_state_date': fields.Datetime.now()})
        
    def action_compute_prix_revient(self):
        if self.taux_change == 0.0:
            raise UserError(u'Le taux de change doit être non nul')
        purchase_obj = self.env['purchase.order']
        purchase_line_obj = self.env['purchase.order.line']
        bex_obj = self.env['budget.expense.report']
        bex_line_obj = self.env['bex.line']
        
        if self.purchase_type == 'purchase_import':
            
            breq_transport = purchase_obj.search(['&', ('parents_ids','=',self.id), ('service_type','=','transport')])
            breq_assurance = purchase_obj.search(['&', ('parents_ids','=',self.id), ('service_type','=','assurance')])
            breq_additionnel = purchase_obj.search(['&', ('parents_ids','=',self.id), ('service_type','=','additionel')])
            breq_droit_douane = purchase_obj.search(['&', ('parents_ids','=',self.id), ('service_type','=','douane')],limit=1)
                  
            bex_transport = bex_obj.search([('breq_id','in',tuple([breq.id for breq in breq_transport]))])
            bex_assurance = bex_obj.search([('breq_id','in',tuple([breq.id for breq in breq_assurance]))])
            bex_additionnel = bex_obj.search([('breq_id','in',tuple([breq.id for breq in breq_additionnel]))])
            bex_droit_douane = bex_obj.search([('breq_id','in',tuple([breq.id for breq in breq_droit_douane]))])

            total_assurance_fret = sum(x.amount_untaxed_bex for x in bex_transport) + sum(x.amount_untaxed_bex for x in bex_assurance)
            cLocTotal = sum(x.amount_untaxed_bex for x in bex_additionnel)
            fob_total = sum(line.product_qty*line.pu_discounted for line in self.order_line)
            caf_total = (fob_total + total_assurance_fret) * self.taux_change
            
            for line in self.order_line:
                if fob_total == 0.0:
                    raise UserError(u'FOB total ne devrait pas être nulle')
                elif line.product_qty <= 0.0:
                    raise UserError(u'La quantité des articles devrait être un nombre positif non nulle')
                else:
                    bex_line_id = bex_line_obj.search([('bex_id','=', bex_droit_douane.id),('purchase_line_id.purchase_line_id','=', line.id)], limit=1)
                    droit_douane = bex_line_id.montant_realise
                    line.cout_revient = (((caf_total + cLocTotal) * ((line.price_subtotal) / fob_total)) + droit_douane) / (line.product_qty)
                    
    def choisir_mode_paiement(self):
                #Generation popup mode de paiement
        ir_model_data = self.env['ir.model.data']        
        try:            
            template_id = ir_model_data.get_object_reference('purchase_heri', 'action_mode_paiement')[1]        
        except ValueError:            
            template_id = False
        
        try:            
            compose_form_id = ir_model_data.get_object_reference('purchase_heri', 'view_mode_paiement_form')[1]        
        except ValueError:            
            compose_form_id = False        
            
        ctx = dict()        
        ctx.update({         
            'default_mode_paiement': self.journal_id.id,   
            'default_model': 'mode.paiement',
            'default_use_template': bool(template_id),            
            'default_template_id': template_id,      
            'default_breq_id': self.id,
        })
        
        return {
        'name': 'Paiement',
        'domain': [],
        'res_model': 'mode.paiement',
        'type': 'ir.actions.act_window',
        'view_mode': 'form',
        'view_type': 'form',
        'views': [(compose_form_id, 'form')],
        'view_id': compose_form_id,
        'context': ctx,
        'target': 'new',
        }
    
    #Achat import state
    def action_aviser_finance(self):
        self.write({'state':'aviser_finance', 'change_state_date': fields.Datetime.now()})
    def action_send_to_bank(self):
        self.write({'state':'ov_to_bank', 'change_state_date': fields.Datetime.now()})
    def action_br_lie_draft(self):
        self.write({'state':'br_lie', 'change_state_date': fields.Datetime.now()})
    
    #Fonction pour budget request stock
    @api.multi
    def creer_bs(self):
        for order in self:
            order._create_picking()
            order.write({'state':'bs', 'change_state_date': fields.Datetime.now()})

    def envoyer_a_approuver(self):
        self.write({'state':'a_approuver', 'change_state_date': fields.Datetime.now()})
        #self._create_picking2()
    
    def verification_stock(self):
        if not self.is_breq_stock:
            return
        location_id = self.env.ref('stock.stock_location_stock')
        dict = {}
        product_list = []
        for line in self.order_line:
            if line.product_id not in product_list:
                product_list.append(line.product_id)
            if dict.get(line.product_id,False):
                dict[line.product_id] += line.product_qty
            else: dict[line.product_id] = line.product_qty     
        for product in product_list:
            total_qty = 0.0
            stock_quant_ids = self.env['stock.quant'].search(['&', ('product_id','=',product.id), ('location_id','=',location_id.id)])
            for quant in stock_quant_ids:
                total_qty += quant.qty
            if total_qty < dict[product]:
                raise UserError(u'La quantité en stock de l\'article '+ product.name +' est insuffisante pour cette demande.')
 
    @api.depends('date_prevu')
    def _compute_date_planned(self):
        for order in self:
            order.date_planned = order.date_prevu
 
class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    qte_prevu = fields.Float(compute="onchange_prod_id", string='Quantité disponible')
    designation_frns = fields.Text(string='Description Fournisseur')
    location_id = fields.Many2one('stock.location', related='order_id.location_id', readonly=True)
    caf = fields.Float(string='CAF')
    cdtd = fields.Float(string='Cout avec droit et taxe de douane')
    cout_revient = fields.Float(string='Prix de revient estimatif')
    purchase_line_id = fields.Many2one('purchase.order.line', 'Purchase Order Line', ondelete='set null', index=True, readonly=True)
    pu_discounted = fields.Float(compute="_compute_pu_discounted", string='Prix unitaire remisé', store=True)
    currency_en_ar = fields.Many2one('res.currency', related='order_id.currency_en_ar', readonly=True)
    
    @api.depends('price_unit','discount')
    def _compute_pu_discounted(self):
        for line in self:
            line.pu_discounted = line.price_unit * (1 - line.discount / 100)
        
    def _suggest_quantity(self):
        res = super(PurchaseOrderLine, self)._suggest_quantity()
        self.product_qty = 0.0
        return res
    
    @api.onchange('product_id')
    def onchange_prod_id(self):
        for line in self:
            if line.order_id.is_breq_stock and not line.location_id:
                raise UserError("La zone d'emplacement source ne doit pas être vide dans un Budget Request Stock")
            #line.qte_prevu = line.product_id.virtual_available
            
            location_src_id = line.location_id
            total_qty_available = 0.0
            total_reserved = 0.0
            liste_picking_ids = []
            
            stock_quant_ids = line.env['stock.quant'].search(['&', ('product_id','=',line.product_id.id), ('location_id','=', location_src_id.id)])
            line_ids = line.search([('order_id.is_breq_stock','=', True), ('order_id.state','!=', 'cancel'), \
                                                               ('product_id','=', line.product_id.id), ('location_id','=', location_src_id.id), \
                                                               ])
            #recuperer tous les articles reserves dans bci
            bci_ids = line.env['stock.move'].search([('picking_id.mouvement_type','=', 'bci'), \
                                                                   ('picking_id.state','not in', ('draft','done','cancel')), \
                                                                   ('product_id','=', line.product_id.id)
                                                                   ])  
            total_bci_reserved = sum(x.product_uom_qty for x in bci_ids)
            total_reserved = sum(x.product_qty for x in line_ids if x.order_id.bs_id.state not in ('done','cancel'))
            for quant in stock_quant_ids:
                total_qty_available += quant.qty
            line.qte_prevu = total_qty_available - total_reserved - total_bci_reserved
    
    @api.onchange('product_id')
    def onchange_product_id(self):
        res = super(PurchaseOrderLine, self).onchange_product_id()
        if self.product_id:
            self.price_unit = self.product_id.standard_price
            ref = ""
            desc = ""
            if self.product_id.ref_fournisseur not in ('', False) :
                ref = "["+self.product_id.ref_fournisseur+"]"
            if self.product_id.desc_fournisseur not in ('', False) :
                desc = self.product_id.desc_fournisseur
            self.designation_frns = ref+" "+ str(desc)
        return res
    
    @api.onchange('product_qty')
    def onchange_product_qty(self):
        if self.order_id.is_breq_stock: 
            product_seuil_id = self.env['product.product'].search([('id','=',self.product_id.id)])
            product_seuil = product_seuil_id.security_seuil
            qte_restant = self.qte_prevu - self.product_qty

            if self.qte_prevu < self.product_qty:
#                 self.product_qty = self.qte_prevu
                return {
                        'warning': {
                                    'title': 'Avertissement!', 'message': 'La quantité demandée réduite au disponible dans le magasin: '+str(self.qte_prevu)
                                },
                        'value': {
                                'product_qty': self.qte_prevu,
                                }
                        }
            elif self.qte_prevu > self.product_qty and qte_restant < product_seuil:
                return {
                        'warning': {
                                    'title': 'Avertissement - Seuil de sécurité!', 'message': 'Le seuil de securité pour cet article est "'+str(product_seuil)+'". Ce seuil est atteint pour cette demande. La quantité restante serait "'+str(qte_restant)+'" qui est en-dessous de seuil de sécurité.'
                                },
                        'value': {
                                'product_qty': self.product_qty,
                                }
                        }
        elif self.order_id.parent_id:
            total_qty = 0.0
            qty_breq_fille = 0.0
            allowed_qty = 0.0
            
            #Quantité total de l'article en cours dans BREq Mère
            order_line = self.env['purchase.order.line'].search([('order_id','=',self.order_id.parent_id.id), ('product_id','=',self.product_id.id)])
            if order_line:
                total_qty = sum(x.product_qty for x in order_line)
                breq_fille_line = self.env['purchase.order.line'].search([('order_id.parent_id','=',self.order_id.parent_id.id), ('product_id','=',self.product_id.id)])
                if breq_fille_line:
                    qty_breq_fille = sum(x.product_qty for x in breq_fille_line)
                allowed_qty = total_qty - qty_breq_fille
                if self.product_qty > allowed_qty:
                    return {
                            'warning': {
                                        'title': 'Avertissement - Quantité commandée!', 'message': 'La quantité de l\'article dépasse la quantité du Budget Request Mère !'
                                    },
                            'value': {
                                    'product_qty': total_qty,
                                    }
                            }
            else:
                raise UserError('Article introuvable!')
            
        return

    @api.multi
    def _create_bex_lines(self, bex):
        bex_line = self.env['bex.line']
        for line in self:
            vals = {
                'name': line.name or '',
                'product_id': line.product_id.id,
                'qty_done': line.product_qty,
                'product_uom': line.product_uom.id,
                'breq_id': line.order_id.id,
                'purchase_line_id': line.id,
                'price_unit': line.pu_discounted,
                'bex_id' :  bex.id,
                'product_qty' : line.product_qty,
                'prix_unitaire' : line.price_unit,
                'montant_br' : line.price_subtotal,
                'purchase_type': line.order_id.purchase_type,
            }
            if line.order_id.purchase_type == 'purchase_import':
                vals['prix_unitaire'] = 0.0
            
            bex_lines = bex_line.create(vals)
        return True
    
    @api.multi
    def _create_stock_moves(self, picking):
        moves = self.env['stock.move']
        done = self.env['stock.move'].browse()
        for line in self:
            if line.product_id.type not in ['product', 'consu', 'service']:
                continue
            qty = 0.0
            price_unit = line._get_stock_move_price_unit()
            for move in line.move_ids.filtered(lambda x: x.state != 'cancel'):
                qty += move.product_qty
            template = {
                'name': line.name or '',
                'product_id': line.product_id.id,
                'product_uom': line.product_uom.id,
                'product_uom_qty': line.product_qty,
                'date': line.order_id.date_order,
                'date_expected': line.date_planned,
                'location_dest_id': line.env.ref('purchase_heri.stock_location_virtual_heri').id,
                'location_id': line.order_id.location_id.id,
                'picking_id': picking.id,
                'partner_id': line.order_id.dest_address_id.id,
                'move_dest_id': False,
                'state': 'draft',
                'purchase_line_id': line.id,
                'company_id': line.order_id.company_id.id,
                'price_unit': price_unit,
                'picking_type_id': line.env.ref('purchase_heri.type_preparation_heri').id,
                'group_id': line.order_id.group_id.id,
                'procurement_id': False,
                'origin': line.order_id.name,
                'route_ids': line.order_id.picking_type_id.warehouse_id and [(6, 0, [x.id for x in line.order_id.picking_type_id.warehouse_id.route_ids])] or [],
                'warehouse_id':line.order_id.picking_type_id.warehouse_id.id,
            }
            
            diff_quantity = line.product_qty - qty
            for procurement in line.procurement_ids:
                # If the procurement has some moves already, we should deduct their quantity
                sum_existing_moves = sum(x.product_qty for x in procurement.move_ids if x.state != 'cancel')
                existing_proc_qty = procurement.product_id.uom_id._compute_quantity(sum_existing_moves, procurement.product_uom)
                procurement_qty = procurement.product_uom._compute_quantity(procurement.product_qty, line.product_uom) - existing_proc_qty
                if float_compare(procurement_qty, 0.0, precision_rounding=procurement.product_uom.rounding) > 0 and float_compare(diff_quantity, 0.0, precision_rounding=line.product_uom.rounding) > 0:
                    tmp = template.copy()
                    tmp.update({
                        'product_uom_qty': min(procurement_qty, diff_quantity),
                        'move_dest_id': procurement.move_dest_id.id,  #move destination is same as procurement destination
                        'procurement_id': procurement.id,
                        'propagate': procurement.rule_id.propagate,
                    })
                    done += moves.create(tmp)
                    diff_quantity -= min(procurement_qty, diff_quantity)
            if float_compare(diff_quantity, 0.0, precision_rounding=line.product_uom.rounding) > 0:
                template['product_uom_qty'] = diff_quantity
                done += moves.create(template)
        return done
    
class PurchaseImportType(models.Model):
    _name = 'purchase.import.type'
    
    name = fields.Char(string="Type",required=True)
