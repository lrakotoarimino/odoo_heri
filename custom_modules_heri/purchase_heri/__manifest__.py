# -*- coding: utf-8 -*-
{
    'name': 'Purchase module for HERi NEW',
    'version': '1.0',
    'category': 'Purchase Management',
    'sequence': 0,
    'description': """Module de gestion des achats pour Heri""",
    'website': 'https://www.ingenosya.mg',
    'depends': ['purchase','stock'],
    'data': [
                'views/stock_view.xml',
                'views/purchase_view.xml',
                'views/stock_piking_view.xml',
                'views/purchase_wkf.xml',
                'security/security.xml',
                'security/ir.model.access.csv',
             ],
    'demo': [],
    'test': [],
    'installable': True,
    'application': True,
    'auto_install': False,
}