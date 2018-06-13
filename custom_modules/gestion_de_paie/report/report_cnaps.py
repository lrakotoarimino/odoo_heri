# -*- coding: utf-8 -*-

from odoo import api, models
import datetime

class report_cnaps(models.AbstractModel):
    _name = 'report.gestion_de_paie.report_cnaps'

    def _get_date_start_filter(self):
        #TODO recuperer la date de debut de filtre
        return "2017-03"
    
    def _get_date_end_filter(self):
        #TODO recuperer la date de fin de filtre
        return "2017-06"
    
    def _get_passport_or_cin(self, obj):
        if obj.employee_id.num_cin:
            return obj.employee_id.num_cin
        elif obj.employee_id.passport_id:
            return obj.employee_id.passport_id
        else:
            return "-"
    
    def _get_annee_mois(self, ddd):
        strpdate = datetime.datetime.strptime(ddd, "%Y-%m-%d")
        return str(strpdate.year) + "-" + str(strpdate.month)
    

    @api.multi
    def render_html(self, docids, data=None):
        #=======================================================================
        # self.model = self.env.context.get('active_model')
        # docs = self.env[self.model].browse(self.env.context.get('active_ids', []))
        #=======================================================================
        
        docargs = {
            'doc_ids': docids,
            'doc_model': 'cnaps',
            'docs': self.env['cnaps'].browse(docids),
            'get_date_start_filter': self._get_date_start_filter,
            'get_date_end_filter': self._get_date_end_filter,
            'get_annee_mois': self._get_annee_mois,
            'get_passport_or_cin': self._get_passport_or_cin,
            'data': data,
        }
        return self.env['report'].render('gestion_de_paie.report_cnaps', docargs)

     

    
    
