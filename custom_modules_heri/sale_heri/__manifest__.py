# -*- coding: utf-8 -*-
{
    'name': 'Sale module for Heri',
    'version': '1.0',
    'category': 'Sale Management',
    'sequence': 0,
    'description': """Module de gestion de vente de HERi""",
    'website': 'https://www.ingenosya.mg',
    'depends': ['sale','hr'],
    'data': [
                'views/sale_heri_view.xml',
                'views/res_partner_view.xml',
                'views/res_diplome_view.xml',
                'views/product_family_view.xml',
                'data/sale_heri_data.xml',
             ],
    'demo': [],
    'test': [],
    'installable': True,
    'application': True,
    'auto_install': False,
}