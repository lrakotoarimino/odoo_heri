# -*- coding: utf-8 -*-


from odoo import api, models, fields

from odoo.addons.base.res.res_partner import WARNING_MESSAGE, WARNING_HELP


class ProductProduct(models.Model):
    _name = 'product.product'
    _inherit = 'product.product'
    
    #Redifintion afin recuperer les budget request (non stock)
    @api.multi
    def _purchase_count(self):
        domain = [
            ('order_id.state', 'not in', ['nouveau', 'cancel']),
            ('product_id', 'in', self.mapped('id')),
            ('order_id.is_breq_stock', '=', False), 
        ]
        PurchaseOrderLines = self.env['purchase.order.line'].search(domain)
        for product in self:
            product.purchase_count = len(PurchaseOrderLines.filtered(lambda r: r.product_id == product).mapped('order_id'))
            

class ProductTemplate(models.Model):
    _inherit = 'product.template'
    
    purchase_line_warn = fields.Selection(WARNING_MESSAGE, 'Purchase Order Line', help=WARNING_HELP, required=False, default="no-message")