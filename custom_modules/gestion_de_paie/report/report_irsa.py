# -*- coding: utf-8 -*-

from odoo import api, models

class report_irsa(models.AbstractModel):
    _name = 'report.gestion_de_paie.report_irsa'
   
    @api.multi
    def render_html(self, docids, data=None):
        #=======================================================================
        # self.model = self.env.context.get('active_model')
        # docs = self.env[self.model].browse(self.env.context.get('active_ids', []))
        #=======================================================================
        
        docargs = {
            'doc_ids': docids,
            'doc_model': 'irsa',
            'docs': self.env['irsa'].browse(docids),
            'data': data,
        }
        return self.env['report'].render('gestion_de_paie.report_irsa', docargs)

     

    
    
