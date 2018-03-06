# -*- coding: utf-8 -*-
{
    'name': 'Sales module for HERi',
    'version': '2.0',
    'category': 'sale',
    'sequence': 0,
    'description': """Sales module for HERi Madagascar""",
    'website': 'https://www.heri.com',
    'depends': ['sale', 'base', 'product', 'stock', 'account', 'report_qweb_element_page_visibility'],
    'data': ['views/invoice_view.xml',
             'views/sale_view.xml',
             'views/res_partner_view.xml',
             'views/product_view.xml',
             'views/stock_view.xml',
             'views/company_view.xml',
             
             'data/paperformat_data.xml',
             'data/inventory_data.xml',
             'data/product_product.xml',
             'data/billing_table.xml',

             'report/report_invoice_redevance.xml',
             ],
    'demo': [],
    'test': [],
    'installable': True,
    'application': True,
    'auto_install': False,
}