# -*- coding: utf-8 -*-

from odoo import fields, models, api
from collections import namedtuple
from odoo.exceptions import UserError
from odoo.tools.float_utils import float_compare
import re

class ModePaiement(models.Model):
    _name = "mode.paiement"
    
    mode_paiement = fields.Many2one('account.journal', string="Mode de paiement", domain=[('type','in',('cash','bank'))])
    bex_id = fields.Many2one('stock.picking.heri')
    
#     @api.model   
#     def create(self, vals):    
#         res = super(ModePaiement, self).create(vals)
#         records = self.env['stock.picking.heri'].browse(res.bex_id.id)
#         return res
    
    def _compute_pump(self):
        
        bex_id = self.bex_id.id
        bex_lines = self.env['bex.line'].search([('bex_id','=',bex_id)])
        
        for record in bex_lines:
            #id des articles
            product_ids = self.env['product.product'].search([('id','=',record.product_id.id)])
            
            for prod in product_ids:
                qte_recu = record.qty_done
                prix_unit = record.prix_unitaire
                qte_total = 0.0
                stock_quant_ids = self.env['stock.quant'].search([('product_id','=',prod.id)])
                                
                for quant in stock_quant_ids:
                    qte_total += quant.qty
                    
                ancien_strd_price = prod.standard_price
                pump = ((qte_recu*prix_unit)+(qte_total*ancien_strd_price))/(qte_recu+qte_total)
                prod.standard_price = pump
                
    def valider_mode_paiement(self):
        self._compute_pump()
        if not self.mode_paiement:
            raise UserError(u'Le mode de paiement ne doit pas être vide.')
        mode_paiement = self.mode_paiement.id
        pick = self.env['stock.picking.heri'].browse(self.bex_id.id)
        pick.write({'journal_id': mode_paiement,'state': 'comptabilise'})

class StockPickingHeri(models.Model):
    _name = "stock.picking.heri" 
    _inherit = 'stock.picking' 
    
    bex_lines = fields.One2many('bex.line', 'bex_id', string="BEX LINES")
    
    remise = fields.Float('Remise (%)')
    purchase_type = fields.Selection([
        ('purchase_stored', 'Achats locaux stockés'),
        ('purchase_not_stored', 'Achats locaux non stockés'),
        ('purchase_import', 'Achats à l\'importation'),
        ('breq_stock', 'Budget request stock'),
    ], string='Type d\'achat')
    
    def _name_change(self):
        for bex in self :
            if bex.origin:
                res = re.findall("\d+", bex.origin)
                longeur_res = len(res)
                res_final = res[longeur_res-1]
                bex.name = "BEX" + "".join(res_final)
            
    name = fields.Char(compute="_name_change")
    breq_id = fields.Many2one('purchase.order', string=u"Budget Request lié")
    
    @api.depends('remise','bex_lines','bex_lines.qty_done','bex_lines.taxes_id','bex_lines.prix_unitaire')
    def _amount_all(self):
        for bex in self:
            amount_untaxed_bex = 0.0
            amount_taxed_bex = 0.0
            remise = 0.0
            if bex.remise:
                remise = bex.remise
                
            for line in bex.bex_lines :
                amount_untaxed_bex += line.montant_realise
                amount_taxed_bex += line.montant_realise_taxe
                
            amount_untaxed_bex = amount_untaxed_bex*(1-(remise/100))
            amount_taxed_bex = amount_taxed_bex*(1-(remise/100))
            
            bex.update({
                'amount_untaxed_bex': amount_untaxed_bex,
                'amount_tax_bex': amount_taxed_bex-amount_untaxed_bex,
                'amount_total_bex': amount_taxed_bex,
                })
            
    def attente_hierarchie(self):
        self.state = 'attente_hierarchie'
        self.change_state_date = fields.Datetime.now()
    def annuler_attente_hierarchie(self):
        self.state = 'assigned'
        self.change_state_date = fields.Datetime.now()
    def hierarchie_ok(self):
        self.state = 'hierarchie_ok'
        self.change_state_date = fields.Datetime.now()
    def annuler_hierarchie_ok(self):
        self.state = 'attente_hierarchie'
        self.change_state_date = fields.Datetime.now()
    def annuler_comptabiliser(self):
        self.state = 'hierarchie_ok'
        self.change_state_date = fields.Datetime.now()
            
    def comptabiliser(self):   
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
            'default_bex_id': self.id,
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
            
    @api.one
    def _get_is_manager(self):
        self.is_manager = False
        current_employee_id = self.env['hr.employee'].search([('user_id','=',self.env.uid)]).id
        manager_id = self.employee_id.coach_id.id
        if current_employee_id == manager_id:
            self.is_manager = True
    
    @api.one
    def _get_is_creator(self):
        self.is_creator = False
        current_employee_id = self.env['hr.employee'].search([('user_id','=',self.env.uid)], limit=1).id
        employee_id = self.employee_id.id
        if current_employee_id == employee_id:
            self.is_creator = True
            
    is_creator = fields.Boolean(compute="_get_is_creator", string='Est le demandeur')
    is_manager = fields.Boolean(compute="_get_is_manager", string='Est un manager')
    
    state = fields.Selection([
        ('draft', 'Nouveau'), ('cancel', 'Cancelled'),
        ('attente_hierarchie','Avis supérieur hierarchique'),
        ('hierarchie_ok','Validation supérieur hierarchique'), 
        ('comptabilise','Comptabilisé')], string='Status', compute='_compute_state',
        copy=False, index=True, readonly=True, store=True, track_visibility='onchange',
        help="Etat du BEX")
    
    #champs du Budget Expense Report
    department_id = fields.Many2one('hr.department', string='Département émetteur/Section analytique')
    objet = fields.Text("Objet de la demande")
    section = fields.Char("Section analytique d’imputation")
    nature = fields.Char("Nature analytique")
    currency_id = fields.Many2one('res.currency')
    
    employee_id = fields.Many2one('hr.employee', string='Demandeur', readonly=True)
    manager_id = fields.Many2one('hr.employee', string='Responsable d\'approbation', readonly=True)
    
    budgetise = fields.Float("Budgetisé")
    cumul = fields.Float("Cumul Real. + ENgag.")
    solde = fields.Float("Solde de budget")
    journal_id = fields.Many2one('account.journal', string='Mode de paiement', domain=[('type', 'in', ('bank', 'cash'))])
    
    amount_untaxed_bex = fields.Float(compute='_amount_all', string='Montant HT', readonly=True, store=True)
    amount_tax_bex = fields.Float(compute='_amount_all', string='Taxes', readonly=True, store=True)
    amount_total_bex = fields.Float(compute='_amount_all', string='Total', readonly=True, store=True)
    
    change_state_date = fields.Datetime(string="Date changement d\'état", readonly=True, help="Date du dernier changement d\'état.")
    
    #BUdget request
    amount_untaxed_breq = fields.Float('Montant HT', readonly=True)
    amount_tax_breq = fields.Float('Taxes', readonly=True)
    amount_total_breq = fields.Float('Total', readonly=True)
    
    observation = fields.Text("Obsevations")
    solde_rembourser = fields.Monetary('Solde à rembourser/payer')
    
class BexLine(models.Model):
    _name = "bex.line"
    
    name = fields.Char('Désignation')
    bex_id = fields.Many2one('stock.picking.heri', 'Reference Bex')
    product_id = fields.Many2one('product.product', 'Article')
    product_qty = fields.Float('Quantité BReq',readonly=True)
    qty_done = fields.Float('Quantité reçue')
    prix_unitaire = fields.Float('PU')
    montant_br = fields.Float('Montant BReq',readonly=True)
    montant_realise = fields.Float(compute='_compute_amount', string='Montant Réalisé', readonly=True, store=True)
    montant_realise_taxe = fields.Float(compute='_compute_amount', string='Montant Réalisé taxé', readonly=True, store=True)
    taxes_id = fields.Many2many('account.tax', string='Taxes', domain=['|', ('active', '=', False), ('active', '=', True)])
    
    purchase_type = fields.Selection([
        ('purchase_stored', 'Achats locaux stockés'),
        ('purchase_not_stored', 'Achats locaux non stockés'),
        ('purchase_import', 'Achats à l\'importation')
    ], string='Type d\'achat')
    
    breq_id = fields.Many2one('purchase.order', string='ID Breq')
    purchase_line_id = fields.Many2one('purchase.order.line', string='ID ligne de commande')
    product_uom = fields.Many2one('product.uom', string='Unité de mesure')
    
    @api.depends('qty_done', 'taxes_id')
    def _compute_amount(self):
        for line in self:
            if line.qty_done > line.product_qty or line.qty_done < 0.0:
                raise UserError(u'La quantité reçue doit être inférieur ou égale à la quantité du BReq')
            
            taxes = line.taxes_id.compute_all(line.prix_unitaire, line.bex_id.currency_id, line.qty_done, product=line.product_id, partner=False)
            line.update({
                 'montant_realise': taxes['total_excluded'],
                 'montant_realise_taxe': taxes['total_included'],
            })
            
    
