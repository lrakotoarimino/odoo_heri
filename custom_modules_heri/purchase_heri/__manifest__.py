# -*- coding: utf-8 -*-
{
    'name': 'Purchase module for HERi',
    'version': '1.0',
    'category': 'Purchase Management',
    'sequence': 0,
    'description': """Module de gestion d'achat de Heri""",
    'website': 'https://www.ingenosya.mg',
    'depends': ['purchase','stock'],
    'data': [
                #'data/purchase_heri_data.xml',
                'views/purchase_view.xml',
                'views/purchase_wkf.xml',
                'views/purchase_import_wkf.xml',
                'views/stock_view.xml',
             ],
    'demo': [],
    'test': [],
    'installable': True,
    'application': True,
    'auto_install': False,
}