# -*- coding: utf-8 -*-
{
    'name': 'Sale module for HERi',
    'version': '1.0',
    'category': 'sale',
    'sequence': 0,
    'description': """Module des ventes pour Heri""",
    'website': 'https://www.beheri.com',
    'depends': ['sale'],
    'data': [
                'views/sale_wkf.xml',
                'views/sale_view.xml',
            ],
    'demo': [],
    'test': [],
    'installable': True,
    'application': True,
    'auto_install': False,
}