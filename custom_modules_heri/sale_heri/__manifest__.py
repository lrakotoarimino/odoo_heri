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
                #views
                'views/sale_view.xml',
                'views/sale_ajout_materiel_entrepreneur_view.xml',
                'views/sale_fact_materiel_tiers_view.xml',
                'views/budget_request_stock_view.xml',
                'views/stock_location_view.xml',
                #workflow
                'views/sale_wkf.xml',
                'views/sale_ajout_materiel_entrepreneur_wkf.xml',
                'views/sale_fact_materiel_tiers_wkf.xml',
            ],
    'demo': [],
    'test': [],
    'installable': True,
    'application': True,
    'auto_install': False,
}