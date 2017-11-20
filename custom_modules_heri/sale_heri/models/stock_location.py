# -*- coding: utf-8 -*-

from datetime import datetime
from dateutil import relativedelta

from odoo import api, fields, models, _
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT


class Location(models.Model):
    _inherit = "stock.location"
   
    is_kiosque = fields.Boolean(string='Est un kiosque ?')
    region_id = fields.Many2one('res.region',string="Région de l'activité")
    date_contrat = fields.Datetime(string="Date du contrat", help="Date d'etablissement du contrat")
    plus_une_redevance = fields.Boolean(string='A déjà  effectué au moins une facturation redevance mensuelle')