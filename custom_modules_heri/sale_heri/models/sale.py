# -*- coding: utf-8 -*-

from odoo import fields, models, api
from collections import namedtuple
from odoo.exceptions import UserError
from odoo.tools.float_utils import float_compare
import re
import time
from docutils.nodes import Invisible
from datetime import datetime

class SaleHeri(models.Model):
    _inherit = "sale.order"
    _description = "Facturation redevance mensuelle"
    
    @api.model
    def create(self, vals):
        res = super(SaleHeri, self).create(vals)
        vals['is_create'] = True
        return res
    
    kiosque_id = fields.Many2one('stock.location', string='Kiosque *') 
    
    facturation_type = fields.Selection([
            ('facturation_redevance','Redevance mensuelle'),
            ('materiel_loue', 'Materiel Loué'),
            ('facturation_tiers', 'Tiers'),
            ('facturation_entrepreneurs', 'Entrepreneurs'),
        ], string='Type de Facturation')
    #partner_id = fields.Many2one('res.partner', string='Customer', readonly=True, states={'draft': [('readonly', False)], 'sent': [('readonly', False)],'nouveau': [('readonly', False)]}, required=True, change_default=True, index=True, track_visibility='always')
    correction_et_motif = fields.Text(string="Correction et Motif")
    purchase_id= fields.Many2one('purchase.order')
    state = fields.Selection([
        ('draft', 'Nouveau'),
        ('correction_et_motif', 'Correction et Motif Call Center'),
        ('correction_et_motif_finance', 'Correction et Motif Finance'),
        ('observation_dg', 'Observation du DG'),
        ('verif_pec', 'Verification des PEC'),
        ('facture_generer', 'Facture Generee'),
        ('breq_stock', 'Breq Stock Generee'),  
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
            for line in order:
                line.order_line.unlink()
            stock_quant_ids = order.env['stock.quant'].search([('location_id','=',order.kiosque_id.id)])
            for prod in stock_quant_ids:
                in_date_list = []
                for product in prod:
                    if product.in_date not in in_date_list:
                        in_date_list.append(product.in_date) 
                for date in in_date_list:
                    quants = order.env['stock.quant'].search(['&', ('in_date','=',date), ('location_id','=',order.kiosque_id.id)])
                    total_qty = 0.0
                    for q in quants:
                        product_list = []
                        if q.product_id not in product_list:
                            product_list.append(q.product_id)
                    for p in product_list:
                        product_quant = order.env['stock.quant'].search(['&', ('product_id','=',p.id), '&', ('in_date','=',date), ('location_id','=',order.kiosque_id.id)])
                        for quant in product_quant:
                            total_qty += quant.qty
                        order_line = self.env['sale.order.line']
                        duree = str((datetime.now()-datetime.strptime(date, "%Y-%m-%d %H:%M:%S")).days)
                        vals = {
                            'name': p.name,
                            'product_id': p.id,
                            'product_uom': p.uom_id.id,
                            'product_uom_qty': total_qty,
                            'order_id': order.id,
                            'price_unit': p.lst_price,
                            'date_arrivee': date,
                            'nbre_jour_arrive': duree,
                        }
                        order.order_line.create(vals)
    
    #facturation redevance
    def generation_list(self):
        self.write({'state':'draft'})
    def correction_motif_call(self):
        self.write({'state':'correction_et_motif'}) 
    def correction_motif_finance(self):
        self.write({'state':'correction_et_motif_finance'}) 
    def observation_dg(self):
        self.write({'state':'observation_dg'}) 
    def verif_pec(self):
        self.write({'state':'verif_pec'}) 
    def generation_facture_sms(self):
        for order in self:
            order.state = 'sale'
            order.confirmation_date = fields.Datetime.now()
            if self.env.context.get('send_email'):
                self.force_quotation_send()
            #order.order_line._action_procurement_create()
        if self.env['ir.values'].get_default('sale.config.settings', 'auto_done_setting'):
            self.action_done()
        return True
    
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
    
                
    @api.multi
    def _create_breq_stock(self):
        breq_stock_obj = self.env['purchase.order']
        for order in self:
            vals = {
                    'partner_id': order.partner_id.id,
                    'origin': order.name,
                    'breq_id_sale': order.id,                     
                    'company_id': order.company_id.id,
                    'is_breq_stock' : True,
                    'move_type': 'direct',
                    'location_id':15, #order.partner_id.property_stock_supplier.id,
                    'company_id': order.company_id.id,
                    'amount_untaxed': order.amount_total,
                    'date_planned':fields.Datetime.now(),
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
    
    #facturation aux tiers   
    def generation_breq_stock(self):
        self.write({'state':'breq_stock'}) 
     
class SaleOrderLineHeri(models.Model):
    _inherit = 'sale.order.line'
     
    date_arrivee = fields.Datetime(string='Date d\'arrivée')
    nbre_jour_arrive = fields.Float(string='Nombre de jour d\'arrivé', default=0.0)
     
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
            ('open', 'SMS envoyé'),
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
        self.write({'state':'open'})
    
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