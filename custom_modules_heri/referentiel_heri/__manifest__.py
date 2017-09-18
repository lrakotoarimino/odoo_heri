# -*- coding: utf-8 -*-
{
    'name': 'Referentiel HERi',
    'version': '1.0',
    'category': 'Referentiel',
    'sequence': 0,
    'description': """Module de gestion des referentiels de HERi""",
    'website': 'https://www.ingenosya.mg',
    'depends': ['purchase','sale','hr','stock'],
    'data': [
        'views/res_partner_view.xml',
        'views/product_view.xml',
        'views/res_diplome_view.xml',
        'views/res_region_view.xml',
             ],
    'demo': [],
    'test': [],
    'installable': True,
    'application': True,
    'auto_install': False,
}