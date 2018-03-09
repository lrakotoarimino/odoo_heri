# -*- coding: utf-8 -*-

from odoo import models, fields


class ResCompany(models.Model):
    _inherit = 'res.company'
    
    num_stat = fields.Char(string="Num stat")
    nif = fields.Char(string="NIF")
    rcs = fields.Char(string="RCS")
    cif = fields.Char(string="CIF")
    
    bank_bni = fields.Char(string="BNI")
    acces_bank = fields.Char(string="Acces Bank")
    mvola = fields.Char(string="M Vola")
    airtel_money = fields.Char(string="Airtel Money")
    orange_money = fields.Char(string="Orange Money")
