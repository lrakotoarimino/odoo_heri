# -*- coding: utf-8 -*-

from odoo import fields, models, api
from collections import namedtuple
from odoo.exceptions import UserError, RedirectWarning, ValidationError
from odoo.tools.float_utils import float_compare
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.tools.translate import _
import re
import time
from docutils.nodes import Invisible
from datetime import datetime, date
from pyparsing import lineEnd

class SaleHeri(models.Model):
    _inherit = "sale.order"
    _description = "Facturation redevance mensuelle"
    
    @api.model
    def create(self, vals):
        res = super(SaleHeri, self).create(vals)
        vals['is_create'] = True
        return res
    #champ pour recupérer le kiosque
    kiosque_id = fields.Many2one('stock.location', string='Kiosque *') 
    location_id = fields.Many2one('stock.location', string='Magasin d\'origine *') 
    facturation_type = fields.Selection([
            ('facturation_redevance','Redevance mensuelle'),
            ('materiel_loue', 'Materiel Loué'),
            ('facturation_tiers', 'Tiers'),
            ('facturation_entrepreneurs', 'Entrepreneurs'),
            ('facturation_mat_mauvais_etat', 'Matériels mauvais état'),
        ], string='Type de Facturation')
    correction_et_motif = fields.Text(string="Correction et Motif")
    purchase_id= fields.Many2one('purchase.order')
    calendar_id = fields.Many2one('res.calendar', string='Calendrier de facturation')
    
    def _get_date_debut_facturation(self):
        if self.facturation_type == 'facturation_redevance':
            calendar = self.env.ref('sale_heri.calendrier_facturation_redevance')
            if not calendar.last_month:
                return False
            else:
                return calendar.last_month
    
    def _get_date_fin_facturation(self):
        if self.facturation_type == 'facturation_redevance':
            calendar = self.env.ref('sale_heri.calendrier_facturation_redevance')
            if not calendar.current_month:
                return False
            else:
                return calendar.current_month
        
    date_debut_facturation = fields.Datetime(string="Date debut de la facturation", default=_get_date_debut_facturation, help="Date debut de la facturation") 
    date_fin_facturation = fields.Datetime(string="Date fin de la facturation", default=_get_date_fin_facturation, help="Date fin de la facturation") 
    
    state = fields.Selection([
        ('draft', 'Nouveau'),
        ('controle_technicien', 'Contrôle du technicien'),
        ('materiel_bon_etat', 'Matérel en bon état'),
        ('materiel_mauvais_etat', 'Matériel en mauvais état'),
        ('correction_et_motif', 'Correction et Motif Call Center'),
        ('correction_et_motif_finance', 'Correction et Motif Finance'),
        ('observation_dg', 'Observation du DG'),
        ('verif_pec', 'Verification des PEC'),
        ('facture_generer', 'Facture Generée'),
        ('breq_stock','Budget request stock'),
        ('solvabilite_ok','Contrôle de solvabilité'),
        ('capacite_ok','Contrôle capacité kiosque'),
        ('preparation_test','Préparation matériels pour test'),
        ('test','Test des matériels'),
        ('sent', 'Quotation Sent'),
        ('sale', 'Génération facture SMS'),
        ('done', 'Locked'),
        ('cancel', 'Cancelled'),
        ], string='Status', readonly=True, copy=False, index=True, track_visibility='onchange',default='draft')
    
    def get_employee_id(self):
        employee_id = self.env['hr.employee'].search([('user_id','=',self.env.uid)])
        if employee_id:
            return employee_id[0].id
        return False
    
    employee_id = fields.Many2one('hr.employee', string='Demandeur', default=get_employee_id, readonly=True)
    is_creator = fields.Boolean(compute="_get_is_creator", string='Est le demandeur')
                     
    @api.one
    def _get_is_creator(self):
        self.is_creator = False
        current_employee_id = self.env['hr.employee'].search([('user_id','=',self.env.uid)], limit=1).id
        employee_id = self.employee_id.id
        if current_employee_id == employee_id:
            self.is_creator = True
    
    @api.onchange('kiosque_id')
    def onchange_kiosque_id(self):
        if not self.kiosque_id:
            self.partner_id = False
            return
        
        partner_id = self.env['res.partner'].search([('kiosque_id','=',self.kiosque_id.id)], limit=1)
        if partner_id:
            self.partner_id = partner_id.id
        else: 
            self.partner_id = False
            
    @api.multi       
    def action_generer_redevance(self):
        for order in self:
            nbr_jour_frais_base = 0.0
            calendar = order.env.ref('sale_heri.calendrier_facturation_redevance')   
            if not calendar.last_month and not calendar.current_month:
                raise UserError('Veuillez renseigner le calendrier de la facturation !')
            else:
                for line in order:
                    line.order_line.unlink()
                #implementation frais de base du kiosque par mois
                order_line = self.env['sale.order.line']
                product_frais_base_id = order.env.ref('sale_heri.product_frais_base')
                date_contrat = datetime.strptime(order.kiosque_id.date_contrat, "%Y-%m-%d %H:%M:%S")
                last_month = datetime.strptime(calendar.last_month, "%Y-%m-%d %H:%M:%S")
                current_month = datetime.strptime(calendar.current_month, "%Y-%m-%d %H:%M:%S")
                if not date_contrat:
                    raise UserError('Veuillez renseigner la date du debut du contrat !')
                if date_contrat > last_month and date_contrat < current_month and datetime.now() >= current_month:
                    effet = (current_month - date_contrat).days
                    nbr_jour_frais_base = float(effet)/31
                elif date_contrat < last_month and order.kiosque_id.premiere_redevance and datetime.now() >= current_month:
                    nbr_jour_frais_base = 1
                elif date_contrat < last_month and not order.kiosque_id.premiere_redevance and datetime.now() >= current_month:
                    effet = (current_month - date_contrat).days
                    nbr_jour_frais_base = float(effet)/31
                elif datetime.now() < current_month:
                    raise UserError('La date d\'etablissement de la facture redevance serait apres le 25 du mois en cours 1')
                elif date_contrat >= current_month:
                    raise UserError('La date d\'etablissement de la facture redevance serait apres le 25 du mois en cours 2')
                for p in product_frais_base_id:
                    vals = {
                        'name': 'Frais de base du kiosque',
                        'product_id': p.id,
                        'product_uom': p.uom_id.id,
                        'qte_article': 1,
                        'product_uom_qty': nbr_jour_frais_base,
                        'order_id': order.id,
                        'price_unit': order.kiosque_id.region_id.frais_base,
                        'date_arrivee': date_contrat,
                        'nbre_jour_detention': nbr_jour_frais_base,
                    }
                    order.order_line.create(vals)
                stock_quant_ids = order.env['stock.quant'].search([('location_id','=',order.kiosque_id.id)])
                #Trier les stock quant par date d'arrivee du materiel
                #stocker toutes les dates d'arrivees des materiels du kiosque dans une liste brute
                in_date_list_brut = []
                for date in stock_quant_ids:
                    in_date_list_brut.append(date.date_arrivee_reelle) 
                #Trier ces dates de facon a ce qu'il n'y a plus de redondance
                in_date_list = []
                for date_final in in_date_list_brut:
                    if date_final not in in_date_list:
                        in_date_list.append(date_final) 
                var = in_date_list
                for date in in_date_list:
                    quants = order.env['stock.quant'].search(['&', ('date_arrivee_reelle','=',date), ('location_id','=',order.kiosque_id.id)])
                    product_redevance_list = []
                    product_location_list = []
                    for q in quants:
                        if q.product_id not in product_redevance_list and q.product_id.frais_type == 'redevance':
                            product_redevance_list.append(q.product_id)
                        elif q.product_id not in product_location_list and q.product_id.frais_type == 'location':
                            product_location_list.append(q.product_id)
                    #Implementation redevance fixe pour les materiels productifs dans les lignes des articles
                    for p in product_redevance_list:
                        nbre_jour_detention_materiel_prod = 0.0
                        product_quant = order.env['stock.quant'].search(['&', ('product_id','=',p.id), '&', ('date_arrivee_reelle','=',date), ('location_id','=',order.kiosque_id.id)])
                        date_arrivee = datetime.strptime(date, "%Y-%m-%d %H:%M:%S")
                        if not date_arrivee:
                            raise UserError('Veuillez renseigner la date d\'arrivee du materiel!')
                        if date_arrivee > last_month and date_arrivee < current_month and datetime.now() >= current_month:
                            effet = (current_month - date_arrivee).days
                            nbre_jour_detention_materiel_prod = float(effet)/31
                        elif date_arrivee <= last_month and datetime.now() >= current_month:
                            nbre_jour_detention_materiel_prod = 1
                        elif datetime.now() < current_month:
                            raise UserError('La date d\'etablissement de la facture redevance serait apres le 25 du mois en cours 3')
                        elif date_arrivee >= current_month:
                            raise UserError('La date d\'etablissement de la facture redevance serait apres le 25 du mois en cours 4')
                        qte_article = 0.0
                        for quant in product_quant:
                            qte_article += quant.qty
                        #La quantite de la commande = nombre jour d'effet x quantite de l'article
                        product_qty = qte_article*nbre_jour_detention_materiel_prod
                        vals = {
                            'name': 'Redevance fixe pour materiels productifs / mois',
                            'product_id': p.id,
                            'product_uom': p.uom_id.id,
                            'qte_article': qte_article,
                            'product_uom_qty': product_qty,
                            'order_id': order.id,
                            'price_unit': p.lst_price,
                            'date_arrivee': date,
                            'nbre_jour_detention': nbre_jour_detention_materiel_prod,
                        }
                        order.order_line.create(vals)   
                    #Implementation frais de location par jour dans les lignes des articles
                    for p in product_location_list:
                        nbre_jour_detention_lampe = 0.0
                        product_quant = order.env['stock.quant'].search(['&', ('product_id','=',p.id), '&', ('date_arrivee_reelle','=',date), ('location_id','=',order.kiosque_id.id)])
                        date_arrivee = datetime.strptime(date, "%Y-%m-%d %H:%M:%S")
                        if not date_arrivee:
                            raise UserError('Veuillez renseigner la date d\'arrivee du materiel!')
                        if date_arrivee > last_month and date_arrivee < current_month and datetime.now() >= current_month:
                            nbre_jour_detention_lampe = float((current_month - date_arrivee).days)
                        elif date_arrivee <= last_month and datetime.now() >= current_month:
                            nbre_jour_detention_lampe = float((current_month - last_month).days)
                        elif datetime.now() < current_month:
                            raise UserError('La date d\'etablissement de la facture redevance serait apres le 25 du mois en cours 5')
                        elif date_arrivee >= current_month:
                            raise UserError('La date d\'etablissement de la facture redevance serait apres le 25 du mois en cours 6')
                        qte_article = 0.0
                        for quant in product_quant:
                            qte_article += quant.qty
                        #La quantite de la commande = nombre jour d'effet x quantite de l'article
                        product_qty = qte_article*nbre_jour_detention_lampe
                        vals = {
                            'name': 'Frais de location / jour',
                            'product_id': p.id,
                            'product_uom': p.uom_id.id,
                            'qte_article': qte_article,
                            'product_uom_qty': product_qty,
                            'order_id': order.id,
                            'price_unit': p.lst_price,
                            'date_arrivee': date,
                            'nbre_jour_detention': nbre_jour_detention_lampe,
                        }
                        order.order_line.create(vals)   
                                
    #facturation redevance
    def generation_list(self):
        self.write({'state':'draft'})
    def correction_motif_call(self):
        for order in self:
            if not order.order_line:
                raise UserError("Les lignes de la facturation ne devraient pas être vide")
            else:
                order.write({'state':'correction_et_motif'}) 
    def correction_motif_finance(self):
        self.write({'state':'correction_et_motif_finance'}) 
    def observation_dg(self):
        self.write({'state':'observation_dg'}) 
    def verif_pec(self):
        self.write({'state':'verif_pec'}) 
    def generation_facture_sms(self):
        for order in self:
            #Pour dire que le kiosque a deja ete faturee plus d'une fois, quand l'etat est a l'etat "sale"
            order.kiosque_id.premiere_redevance = True
            order.state = 'sale'
            order.confirmation_date = fields.Datetime.now()
            if self.env.context.get('send_email'):
                self.force_quotation_send()
        if self.env['ir.values'].get_default('sale.config.settings', 'auto_done_setting'):
            self.action_done()
        return True
    
    #demande d'ajout de materiel pour l'entrepreneur
    def action_set_draft(self):
        self.write({'state':'draft'})
    def action_solvabilite_ok(self):
        self.write({'state':'solvabilite_ok'})
    def action_capacite_ok(self):
        self._create_breq_stock()
        self.write({'state':'capacite_ok'})
    def action_preparation_materiel_ok(self):
        self.write({'state':'preparation_test'})
    def action_test_materiel_ok(self):
        self.write({'state':'test'}) 
    
    breq_stock_ids = fields.One2many('purchase.order', string="Breq stock ids", compute='_compute_breq_stock_lie')
    breq_stock_count = fields.Integer(compute='_compute_breq_stock_lie') 
    
    @api.multi
    def _compute_breq_stock_lie(self):
        for order in self:
            breq_stock_child= order.env['purchase.order'].search([('breq_id_sale','=',order.id),('is_breq_stock','=',True)],limit=1)
            if breq_stock_child:
                order.breq_stock_ids = breq_stock_child
                order.breq_stock_count = len(breq_stock_child)
    
    @api.multi
    def action_breq_stock_lie(self):
        action = self.env.ref('sale_heri.action_budget_request_stock_heri_lie')
        result = action.read()[0]
        return result
    
    #action ouvrir budget request stock ajout materiel loué par entrepreneur
    @api.multi
    def action_breq_stock_lie2(self):
        action = self.env.ref('sale_heri.action_budget_request_stock_heri_2')
        result = action.read()[0]
        return result
       
    statut_facture = fields.Selection(compute="_get_statut_facture", string='Etat Facture',
                      selection=[
                             ('draft', 'Nouveau'), ('cancel', 'Cancelled'),
                             ('open','Entierement facturé'),
                             ('paid','Comptabilisé'),
                             ])
    @api.one
    def _get_statut_facture(self):  
        for order in self :
            facture_lie = order.env['account.invoice'].search([('origin','=',order.name)])
            if facture_lie:
                order.statut_facture = facture_lie.state 

            
    @api.multi
    def _create_breq_stock(self):
        breq_stock_obj = self.env['purchase.order']
        for order in self:
            vals = {
                    'partner_id': order.partner_id.id,
                    'origin': order.name,
                    'employee_id': order.env['hr.employee'].search([('user_id','=',order.user_id.id)],limit=1).id,
                    'breq_id_sale': order.id,                     
                    'company_id': order.company_id.id,
                    'is_breq_stock' : True,
                    'is_breq_id_sale' :True,
                    'move_type': 'direct',
                    'location_id': order.location_id.id,
                    'kiosque_id': order.partner_id.kiosque_id.id,
                    'company_id': order.company_id.id,
                    'amount_tax': order.amount_tax,
                    'amount_untaxed': order.amount_untaxed,
                    'amount_total': order.amount_total,
                    'date_planned':fields.Datetime.now(),
                    'mouvement_type':'bs',
                    'justificatif': "C'/est un justificatif",
                    'department_id': order.env['hr.employee'].search([('user_id','=',order.user_id.id)],limit=1).department_id.id,
                    }
            breq_id = breq_stock_obj.create(vals)     
            breq_lines = order.order_line._create_breq_lines(breq_id)        
        return True
    
    
    @api.multi
    def action_view_facture_sms(self):
        invoices = self.mapped('invoice_ids')
        action = self.env.ref('account.action_invoice_tree1').read()[0]
        if len(invoices) > 1:
            action['domain'] = [('id', 'in', invoices.ids)]
        elif len(invoices) == 1:
            action['views'] = [(self.env.ref('sale_heri.facture_sms_form').id, 'form')]
            action['res_id'] = invoices.ids[0]
        else:
            action = {'type': 'ir.actions.act_window_close'}
        return action
    
    @api.multi
    def action_breq_stock_lie_facture(self):
        action = self.env.ref('sale_heri.action_budget_request_stock_heri_lie_facture')
        result = action.read()[0]
        return result
    
    #facturation aux tiers   
    @api.multi
    def generation_breq_stock(self):
        for order in self:
            for line in order.order_line :
                if line.qte_prevu < line.product_uom_qty :
                    raise UserError("Verifiez la quantité demandée par rapport à  la quantité disponible.")
                if line.product_uom_qty <= 0.0:
                    raise UserError("la quantité demandée doit être une valeur positive.")

            order._create_breq_stock()
            order.write({'state':'breq_stock'}) 
     
class SaleOrderLineHeri(models.Model):
    _inherit = 'sale.order.line'
     
    date_arrivee = fields.Datetime(string='Date d\'arrivée')
    nbre_jour_detention = fields.Float(string='Nombre de jour de l\'effet', default=0.0)
    qte_prevu = fields.Float(compute="onchange_prod_id",string='Quantité disponible', readonly=True)
    qte_article = fields.Float(string='Quantité de l\'article', readonly=True)
    location_id = fields.Many2one('stock.location', related='order_id.location_id', readonly=True)
    product_uom_qty = fields.Float(string='Quantity', required=True, default=0.0)
     
    @api.onchange('product_id')
    def onchange_prod_id(self):
        if self.order_id.facturation_type == 'facturation_mat_mauvais_etat':
            location_src_id = self.order_id.kiosque_id
        else:
            location_src_id = self.location_id
        for line in self:
            if not line.location_id and line.order_id.facturation_type in ('facturation_tiers','materiel_loue'):
                raise UserError("Emplacement Heri ne doit pas être vide")
            total_qty_available = 0.0
            total_reserved = 0.0
            liste_picking_ids = []
            
            stock_quant_ids = self.env['stock.quant'].search(['&', ('product_id','=',line.product_id.id), ('location_id','=', location_src_id.id)])
            line_ids = self.env['purchase.order.line'].search([('order_id.is_breq_stock','=', True), ('order_id.state','!=', 'cancel'), \
                                                               ('order_id.bs_id.state','not in', ('done','cancel')), \
                                                               ('product_id','=', line.product_id.id), ('location_id','=', location_src_id.id), \
                                                               ])
            #recuperer tous les articles reserves dans bci
            bci_ids = self.env['stock.move'].search([('picking_id.mouvement_type','=', 'bci'), \
                                                                   ('picking_id.state','not in', ('done','cancel')), \
                                                                   ('product_id','=', line.product_id.id)
                                                                   ])  
            total_bci_reserved = sum(x.product_uom_qty for x in bci_ids)                                                
            total_reserved = sum(x.product_qty for x in line_ids)
            for quant in stock_quant_ids:
                total_qty_available += quant.qty
            line.qte_prevu = total_qty_available - total_reserved - total_bci_reserved
    
    @api.onchange('product_uom_qty')
    def onchange_product_qty(self):
        if self.order_id.facturation_type in ('facturation_tiers','materiel_loue'):
            product_seuil_id = self.env['product.product'].search([('id','=',self.product_id.id)])
            product_seuil = product_seuil_id.security_seuil
            qte_restant = self.qte_prevu - self.product_uom_qty

            if self.qte_prevu < self.product_uom_qty:
#                 self.product_qty = self.qte_prevu
                return {
                        'warning': {
                                    'title': 'Avertissement!', 'message': 'La quantité demandée réduite à la quantité disponible dans le magasin : '+str(self.qte_prevu)
                                },
                        'value': {
                                'product_uom_qty': self.qte_prevu,
                                }
                        }
            elif self.qte_prevu > self.product_uom_qty and qte_restant < product_seuil:
                return {
                        'warning': {
                                    'title': 'Avertissement - Seuil de sécurité!', 'message': 'Le seuil de securité pour cet article est "'+str(product_seuil)+'". Ce seuil est atteint pour cette demande. La quantité restante serait "'+str(qte_restant)+'" qui est en-dessous de la seuil de sécurité.'
                                },
                        'value': {
                                'product_uom_qty': self.product_uom_qty,
                                }
                        }
        return
     
     
    @api.multi
    def _create_breq_lines(self, breq_id):
        breq_line = self.env['purchase.order.line']
        for line in self:
            vals = {
                'name': line.name or '',
                'product_id': line.product_id.id,
                'product_uom': line.product_uom.id,
                'sale_line_id': line.id,
                'product_qty' : line.product_uom_qty,
                'price_unit': line.price_unit,
                'price_subtotal' : line.price_subtotal,
                'date_planned':fields.Datetime.now(),
                'purchase_line_id':line.order_id.id,
                'taxes_id': [(6, 0, line.tax_id.ids)],
                'order_id': breq_id.id,
                
#                 'purchase_type': line.order_id.purchase_type,
            }     
            breq_lines = breq_line.create(vals)
        return True
     
class AccountInvoiceHeri(models.Model):
    _inherit = "account.invoice"
    
    state = fields.Selection([
            ('draft','Draft'),
            ('proforma', 'Pro-forma'),
            ('proforma2', 'Pro-forma'),
            ('attente_envoi_sms', 'Attente d\'envoi SMS'),
            ('pour_visa','Visa'),
            ('open', 'Open'),
            ('paid', 'Paid'),
            ('cancel', 'Cancelled'),
        ], string='Status', index=True, readonly=True, default='draft',
        track_visibility='onchange', copy=False,
        help=" * The 'Draft' status is used when a user is encoding a new and unconfirmed Invoice.\n"
             " * The 'Pro-forma' status is used when the invoice does not have an invoice number.\n"
             " * The 'Open' status is used when user creates invoice, an invoice number is generated. It stays in the open status till the user pays the invoice.\n"
             " * The 'Paid' status is set automatically when the invoice is paid. Its related journal entries may or may not be reconciled.\n"
             " * The 'Cancelled' status is used when user cancel invoice.")

    def action_aviser_callcenter(self):
        self.write({'state':'attente_envoi_sms'})
    def action_envoi_sms(self):
        to_open_invoices = self.filtered(lambda inv: inv.state != 'open')
        if to_open_invoices.filtered(lambda inv: inv.state not in ['proforma2', 'draft', 'attente_envoi_sms']):
            raise UserError(_("Invoice must be in draft or Pro-forma state in order to validate it."))
        to_open_invoices.action_date_assign()
        to_open_invoices.action_move_create()
        to_open_invoices.invoice_validate()
        self.write({'state':'open'})
    def action_pour_visa(self):
        self.action_invoice_open()
        self.write({'state':'open'})
    def imprimer_facture_redevance_duplicata(self):
        self.print_duplicata()
    
class SaleAdvancePaymentInvHeri(models.TransientModel):
    _inherit = "sale.advance.payment.inv"
    
    @api.multi
    def create_invoices(self):
        sale_orders = self.env['sale.order'].browse(self._context.get('active_ids', []))
        sale_orders.generation_facture_sms()
        if self.advance_payment_method == 'all':
            sale_orders.action_invoice_create(final=True)
        else:
            # Create deposit product if necessary
            if not self.product_id:
                vals = self._prepare_deposit_product()
                self.product_id = self.env['product.product'].create(vals)
                self.env['ir.values'].sudo().set_default('sale.config.settings', 'deposit_product_id_setting', self.product_id.id)

            sale_line_obj = self.env['sale.order.line']
            for order in sale_orders:
                if self.advance_payment_method == 'percentage':
                    amount = order.amount_untaxed * self.amount / 100
                else:
                    amount = self.amount
                if self.product_id.invoice_policy != 'order':
                    raise UserError('The product used to invoice a down payment should have an invoice policy set to "Ordered quantities". Please update your deposit product to be able to create a deposit invoice.')
                if self.product_id.type != 'service':
                    raise UserError("The product used to invoice a down payment should be of type 'Service'. Please use another product or update this product.")
                if order.fiscal_position_id and self.product_id.taxes_id:
                    tax_ids = order.fiscal_position_id.map_tax(self.product_id.taxes_id).ids
                else:
                    tax_ids = self.product_id.taxes_id.ids
                so_line = sale_line_obj.create({
                    'name': 'Advance: %s' % (time.strftime('%m %Y'),),
                    'price_unit': amount,
                    'product_uom_qty': 0.0,
                    'order_id': order.id,
                    'discount': 0.0,
                    'product_uom': self.product_id.uom_id.id,
                    'product_id': self.product_id.id,
                    'tax_id': [(6, 0, tax_ids)],
                })
                self._create_invoice(order, so_line, amount)
        if self._context.get('open_invoices', False):
            return sale_orders.action_view_facture_sms()
        return {'type': 'ir.actions.act_window_close'}