# -*- coding: utf-8 -*-

from odoo import api, models
import datetime

class report_ostie(models.AbstractModel):
    _name = 'report.gestion_de_paie.report_ostie'
   
    def _get_annee_mois(self, ddd):
        strpdate = datetime.datetime.strptime(ddd, "%Y-%m-%d")
        return str(strpdate.year) + "-" + str(strpdate.month)
   
    def _get_passport_or_cin(self, obj):
        if obj.employee_id.num_cin:
            return obj.employee_id.num_cin
        elif obj.employee_id.passport_id:
            return obj.employee_id.passport_id
        else:
            return "-"
    
    @api.multi
    def render_html(self, docids, data=None):
        #=======================================================================
        # self.model = self.env.context.get('active_model')
        # docs = self.env[self.model].browse(self.env.context.get('active_ids', []))
        #=======================================================================
        
        docargs = {
            'doc_ids': docids,
            'doc_model': 'ostie',
            'docs': self.env['ostie'].browse(docids),
            'get_annee_mois': self._get_annee_mois,
            'get_passport_or_cin': self._get_passport_or_cin,
            'data': data,
        }
        return self.env['report'].render('gestion_de_paie.report_ostie', docargs)

     

    
    
