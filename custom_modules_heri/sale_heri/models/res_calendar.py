# -*- coding: utf-8 -*-

from datetime import datetime
from odoo import fields, models, api
from collections import namedtuple
from odoo.exceptions import UserError
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.tools.float_utils import float_compare, float_round
from odoo.tools.translate import _
import re
from odoo.exceptions import UserError
import logging
from pychart.arrow import default

class ResCalendar(models.Model):
    _name = "res.calendar"
    
    name = fields.Char(u'Entre deux dates')
    last_month = fields.Datetime(string="Date du mois précedent", help="Date du mois precedent dont le jour est selon le parametre indiqué dans la configuration vente") 
    current_month = fields.Datetime(string="Date du mois en cours", help="Date du mois en cours dont le jour est selon le parametre indiqué dans la configuration vente") 
    
    def _compute_date_faturation_redevance(self):
        calendar = self.env.ref('sale_heri.calendrier_facturation_redevance')
        for c in calendar:
            print 'test OK ok ok ok ok ok ok ok'