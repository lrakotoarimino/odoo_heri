# -*- coding: utf-8 -*-

from odoo import fields, models, api
from odoo.exceptions import UserError
from odoo.tools import float_compare, float_round

class CodeBudgetaireRegion(models.Model):
    _name = "br.region"
    
    region = fields.Char("Région")

class PurchaseHeri(models.Model):
    _inherit = "purchase.order"
    
    @api.multi
    def _create_picking(self):
        StockPickingHeri = self.env['stock.picking']
        for order in self:
            vals = {
                    'picking_type_id': 5,
                    'partner_id': self.partner_id.id,
                    'date': self.date_order,
                    'origin': self.name,
                    'location_dest_id': 18,
                    'location_id': 15,
                    'company_id': self.company_id.id,
                    'move_type': 'direct',
                    }
            move = StockPickingHeri.create(vals)
            move_lines = order.order_line._create_stock_moves(move)
            
        return True
    
    @api.multi
    def _create_bex(self):
        bex_obj = self.env['stock.picking.heri']
        for order in self:
            vals = {
                    'partner_id': order.partner_id.id,
                    'origin': order.name,
                    'department_id': order.department_id.id,
                    'objet': order.objet,
                    'section': order.section,
                    'nature': order.nature,
                    'budgetise': order.budgetise,
                    'cumul': order.cumul,
                    'solde_rembourser': order.solde,
                    'currency_id': order.currency_id.id,
                    'employee_id': order.employee_id.id,
                    'manager_id': order.manager_id.id,
                    'journal_id':order.journal_id.id,
                    'amount_untaxed_breq': order.amount_untaxed,
                    'amount_tax_breq': order.amount_tax,
                    'amount_total_breq': order.amount_total,
                    'breq_id': order.id,
                    'purchase_type': order.purchase_type,
                    
                    'location_id': order.partner_id.property_stock_supplier.id,
                    'location_dest_id': order._get_destination_location(),
                    'picking_type_id': order.picking_type_id.id, 
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
                bx += dict(res.env['stock.picking.heri'].fields_get(allfields=['state'])['state']['selection'])[etat_bex]
            br = dict(res.env['purchase.order'].fields_get(allfields=['state'])['state']['selection'])[res.state]
            
            res.statut_breq_bex = br + " / " + bx
            
    statut_breq_bex = fields.Char(compute="_concate_state", string='Etat BReq/BEX')
    
    justificatif = fields.Text("Justificatif Non prévu/Dépassement")
    state = fields.Selection([
        ('nouveau', 'Nouveau'),
        ('a_approuver', 'Avis supérieur hiérarchique'),
        ('aviser_finance', 'Etablissement OV'),
        ('ov_to_bank', 'OV envoyé à la banque'),
        ('br_lie', 'Prix de revient'),
        ('calcul_pr', 'Prix de revient calculé'),
        ('non_prevue', 'En vérification compta'),
        ('attente_validation', 'En attente validation DG'),
        ('wait_mode', 'En attente paiement finance'),
        ('purchase', 'BEX'),
        ('refuse', 'Refusé'),
        ('done', 'Terminé'),
        ('cancel', 'Annulé'),
        ('bs', 'Bon de sortie'),
        ], string='Etat BReq', readonly=True, default='nouveau', track_visibility='onchange')
    
    purchase_type = fields.Selection([
        ('purchase_stored', 'Achats locaux stockés'),
        ('purchase_not_stored', 'Achats locaux non stockés'),
        ('purchase_import', 'Achats à l\'importation'),
        ('breq_stock', 'Budget request stock'),
    ], string='Type d\'achat',required=True)
    
    purchase_import_type = fields.Selection([
        ('purchase_import_stored', 'Achats à l\'import stockés'),
        ('purchase_import_not_stored', 'Achats à l\'import non stockés')
    ], string='Type d\'achat',track_visibility='onchange')
    
    import_type = fields.Many2one('purchase.import.type',string="Type Import")
        
    department_id = fields.Many2one('hr.department', string='Département émetteur/Section analytique', default=get_department_id, readonly=True)
    objet = fields.Text("Objet de la demande")
    employee_id = fields.Many2one('hr.employee', string='Demandeur', default=get_employee_id, readonly=True)
    manager_id = fields.Many2one('hr.employee', string='Responsable d\'approbation',default=get_manager_id, readonly=True)
    description = fields.Char("Description")
    region_id = fields.Many2one('br.region', string='Région')
    is_manager = fields.Boolean(compute="_get_is_manager", string='Est un manager')
    change_state_date = fields.Datetime(string="Date changement d\'état", readonly=True, help="Date du dernier changement d\'état.") 
    purchase_ids = fields.One2many('purchase.order', string="purchase_ids", compute='_compute_br_lie')
    br_lie_count = fields.Integer(compute='_compute_br_lie')
    parents_ids = fields.Many2one('purchase.order',readonly=True, string='BReq d\'origine')
    date_prevu = fields.Datetime(string="Date prévue")
    modalite_paiement = fields.Float(string='Modalité de paiement')
    
    section = fields.Char("Section analytique d’imputation")
    nature = fields.Char("Nature analytique")
    budgetise = fields.Float("Budgetisé")
    cumul = fields.Float("Cumul Real. + ENgag.")
    solde = fields.Float("Solde de budget")
    statut_budget = fields.Selection(compute="_get_statut_budget", string="Statut", 
                         selection=[('prevu','Prévu'),
                                    ('non_prevu','Non prévu'),
                                    ('depasse','Dépassement')], store=True, default='prevu')
    
    journal_id = fields.Many2one('account.journal', string='Mode de paiement', domain=[('type', 'in', ('bank', 'cash'))])
    is_creator = fields.Boolean(compute="_get_is_creator", string='Est le demandeur')
    
    statut_bex = fields.Selection(compute="_get_statut_bex", string='Etat BEX',
                      selection=[('draft', 'Draft'), 
                                 ('cancel', 'Cancelled'),
                                 ('waiting', 'Waiting Another Operation'),
                                 ('confirmed', 'Waiting Availability'),
                                 ('partially_available', 'Partially Available'),
                                 ('assigned', 'Nouveau'),
                                 ('done', 'Done'),
                                 ('attente_hierarchie','Avis supérieur hierarchique'),
                                 ('hierarchie_ok','Validation supérieur hierarchique'), 
                                 ('comptabilise','Comptabilisé')])
    
    bex_lie_count = fields.Integer(compute='_compute_bex_lie')
    bex_id = fields.One2many('stock.picking.heri', string="bex_ids", compute='_compute_bex_lie')
    @api.multi
    def _compute_bex_lie(self):
        for bx in self:
            bex_child_purchase = self.env['stock.picking.heri'].search([('breq_id','=',bx.id)])
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
        bex_lie = self.env['stock.picking.heri'].search([('breq_id','=',self.id)], limit=1)
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
            purchase_child = self.env['purchase.order'].search([('parents_ids','=',br.id)])
            if purchase_child:
                br.purchase_ids = purchase_child
                br.br_lie_count = len(purchase_child)
         
    @api.multi
    def action_view_br_lie(self):
        action = self.env.ref('purchase_heri.action_br_lie_tree')
        result = action.read()[0]
        return result
    
    @api.depends('solde','budgetise')
    def _get_statut_budget(self):
        for breq in self:
            if self.purchase_type != 'purchase_import':
                if breq.solde > 0.0 and breq.budgetise > 0.0:
                    breq.statut_budget = 'prevu'
                if breq.solde == 0.0 and breq.budgetise==0.0:
                    breq.statut_budget = 'non_prevu'
                if breq.solde < 0.0 and breq.budgetise > 0.0:
                    breq.statut_budget = 'depasse'
            else:
                breq.statut_budget = 'prevu'
            
    
    @api.one
    def _get_is_manager(self):
        self.is_manager = False
        current_employee_id = self.env['hr.employee'].search([('user_id','=',self.env.uid)]).id
        manager_id = self.employee_id.coach_id.id
        if current_employee_id == manager_id:
            self.is_manager = True
            
    def action_a_approuver(self):
        self.write({'state':'a_approuver', 'change_state_date': fields.Datetime.now()})
    def action_refus_superieur(self):
        self.write({'state':'refuse', 'change_state_date': fields.Datetime.now()})
    def action_non_prevu(self):
        self.write({'state':'non_prevue', 'change_state_date': fields.Datetime.now()})
    def action_refus_finance(self):
        self.write({'state':'refuse', 'change_state_date': fields.Datetime.now()})
    def action_attente_validation(self):
        self.write({'state':'attente_validation', 'change_state_date': fields.Datetime.now()})
    def action_refus_dg(self):
        self.write({'state':'refuse', 'change_state_date': fields.Datetime.now()})
    def action_wait_mode(self):
        self.write({'state': 'wait_mode', 'change_state_date': fields.Datetime.now()})
    def action_confirmed(self):
        self.write({'state': 'purchase', 'change_state_date': fields.Datetime.now()})
        self._create_bex()
    
    #Achat import state
    def action_aviser_finance(self):
        self.write({'state':'aviser_finance', 'change_state_date': fields.Datetime.now()})
    def action_send_to_bank(self):
        self.write({'state':'ov_to_bank', 'change_state_date': fields.Datetime.now()})
    def action_br_lie_draft(self):
        self.write({'state':'br_lie', 'change_state_date': fields.Datetime.now()})
    
    #Breq stock
    def creer_bs(self):
        self.write({'state':'bs', 'change_state_date': fields.Datetime.now()})
        self._create_picking()
    def envoyer_a_approuver(self):
        self.write({'state':'a_approuver', 'change_state_date': fields.Datetime.now()})
        self.verification_stock()
    
    def verification_stock(self):
        if self.purchase_type!='breq_stock':
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
        
class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'
    
    @api.onchange('product_id')
    def onchange_product_id(self):
        res = super(PurchaseOrderLine, self).onchange_product_id()
        if self.product_id:
            self.price_unit = self.product_id.standard_price
        return res
    
    @api.multi
    def _create_bex_lines(self, bex):
        bex_line = self.env['bex.line']
        for line in self:
            vals = {
                'name': line.name or '',
                'product_id': line.product_id.id,
                'product_uom': line.product_uom.id,
                'breq_id': line.order_id.id,
                'purchase_line_id': line.id,
                'price_unit': line.price_unit,
                'bex_id' :  bex.id,
                'product_qty' : line.product_qty,
                'prix_unitaire' : line.price_unit,
                'montant_br' : line.price_subtotal,
                'purchase_type': line.order_id.purchase_type,
            }
            
            bex_lines = bex_line.create(vals)
        return True
    
    @api.multi
    def _create_stock_moves(self, picking):
        moves = self.env['stock.move']
        for line in self:
            vals = {
                'name': line.name or '',
                'product_id': line.product_id.id,
                'product_uom': line.product_uom.id,
                'product_uom_qty': line.product_qty,
                'date': line.order_id.date_order,
                'date_expected': line.date_planned,
                'location_id': 15,
                'location_dest_id': 18,
                'picking_id': picking.id,
                'partner_id': line.order_id.dest_address_id.id,
                'move_dest_id': False,
                'state': 'draft',
                'purchase_line_id': line.id,
                'company_id': line.order_id.company_id.id,
                'picking_type_id': 5,
                'group_id': line.order_id.group_id.id,
                'procurement_id': False,
                'origin': line.order_id.name,
                'route_ids': line.order_id.picking_type_id.warehouse_id and [(6, 0, [x.id for x in line.order_id.picking_type_id.warehouse_id.route_ids])] or [],
                'warehouse_id':line.order_id.picking_type_id.warehouse_id.id,
            }
            
            moves_lines = moves.create(vals)
        return True
    
class PurchaseImportType(models.Model):
    _name = 'purchase.import.type'
    
    name = fields.Char(string="Type",required=True)
        
    