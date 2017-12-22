# -*- coding: utf-8 -*-
{
    'name': 'Distribution HERi',
    'version': '1.0',
    'category': 'Stock Management',
    'sequence': 0,
    'description': """Module distribution pour Heri""",
    'website': 'https://www.beheri.mg',
    'depends': ['base','purchase_heri','stock_heri','sale'],
    'data': [
                #views
                'views/distribution_view.xml',
             ],
    'demo': [],
    'test': [],
    'installable': True,
    'application': True,
    'auto_install': False,
}