# -*- coding: utf-8 -*-


from odoo import api, models

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