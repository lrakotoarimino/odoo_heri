# -*- coding: utf-8 -*-

from odoo import fields, models, api
from collections import namedtuple
from odoo.exceptions import UserError
from odoo.tools.float_utils import float_compare
import re

class SaleHeri(models.Model):
    _inherit = "sale.order"
    _description = "Facturation redevance mensuelle"
    
    kiosque_id = fields.Many2one('stock.location', string='Kiosque') 
    
    def get_employee_id(self):
        employee_id = self.env['hr.employee'].search([('user_id','=',self.env.uid)])
        if employee_id:
            return employee_id[0].id
        return False
    
    employee_id = fields.Many2one('hr.employee', string='Demandeur', default=get_employee_id, readonly=True)
    is_creator = fields.Boolean(compute="_get_is_creator", string='Est le demandeur')
        
    @api.model
    def create(self, vals):
        res = super(SaleHeri, self).create(vals)
        vals['is_create'] = True
        return res
             
    @api.one
    def _get_is_creator(self):
        self.is_creator = False
        current_employee_id = self.env['hr.employee'].search([('user_id','=',self.env.uid)], limit=1).id
        employee_id = self.employee_id.id
        if current_employee_id == employee_id:
            self.is_creator = True
    
    @api.onchange('kiosque_id')
    def onchange_kiosque_id(self):
        for order in self:
            client_id = order.env['res.partner'].search([('kiosque_id','=',order.kiosque_id.id)], limit=1)
            order.partner_id = client_id.id
     
    @api.multi       
    def action_generer_redevance(self):
        for order in self:
            for line in order:
                line.order_line.unlink()
            stock_quant_ids = order.env['stock.quant'].search([('location_id','=',order.kiosque_id.id)])
            for prod in stock_quant_ids:
                for product in prod:
                    product_list = []
                    if product.product_id not in product_list:
                        product_list.append(product.product_id) 
                for product in product_list:
                    product_quant = self.env['stock.quant'].search(['&', ('product_id','=',product.id), ('location_id','=',order.kiosque_id.id)])
                    total_qty = 0.0
                    for quant in product_quant:
                        total_qty += quant.qty
                    order_line = self.env['sale.order.line']
                    vals = {
                        'name': product.name,
                        'product_id': product.id,
                        'product_uom': product.uom_id.id,
                        'product_uom_qty': total_qty,
                        'order_id': order.id,
                        'price_unit': product.lst_price,
                    }
                    order.order_line.create(vals)