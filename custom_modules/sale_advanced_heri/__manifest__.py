# -*- coding: utf-8 -*-
{
    'name': 'Sales module for HERi',
    'version': '2.0',
    'category': 'sale',
    'sequence': 0,
    'description': """Sales module for HERi Madagascar""",
    'website': 'https://www.heri.com',
    'depends': ['sale', 'base', 'product'],
    'data': ['views/invoice_view.xml',
             'views/sale_view.xml',
             'views/res_partner_view.xml',
             'views/product_view.xml',
             
             'data/inventory_data.xml',
             'data/product_product.xml',
             ],
    'demo': [],
    'test': [],
    'installable': True,
    'application': True,
    'auto_install': False,
}