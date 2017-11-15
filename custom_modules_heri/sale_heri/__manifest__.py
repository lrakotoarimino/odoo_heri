# -*- coding: utf-8 -*-
{
    'name': 'Sale module for HERi',
    'version': '1.0',
    'category': 'sale',
    'sequence': 0,
    'description': """Module des ventes pour Heri""",
    'website': 'https://www.beheri.com',
    'depends': ['sale','purchase'],
    'data': [
                'views/sale_view.xml',
                'views/sale_fact_materiel_tiers_view.xml',
                'views/sale_fact_materiel_tiers_wkf.xml',
                'views/breq_stock_view.xml',
                'views/sale_wkf.xml',
                'views/stock_location_view.xml',
            ],
    'demo': [],
    'test': [],
    'installable': True,
    'application': True,
    'auto_install': False,
}