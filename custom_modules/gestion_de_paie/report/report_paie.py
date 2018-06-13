# -*- coding: utf-8 -*-

from odoo import api, models

class report_paie(models.AbstractModel):
    _name = 'report.gestion_de_paie.report_paie'

    def _get_total_by_rule_category(self, obj, code):
        payslip_line = self.env['hr.payslip.line']
        rule_cate_obj = self.env['hr.salary.rule.category']

        cate_ids = rule_cate_obj.search([('code', '=', code)])

        category_total = 0
        if cate_ids:
            payslip_lines = payslip_line.search([('slip_id', '=', obj.id),('category_id', '=', cate_ids[0].id )])
            for line in payslip_lines:
                category_total += line.total

        return category_total
    
    def _get_employe_line(self, obj, parent_line):
        
        payslip_line = self.env['hr.payslip.line']

        line_ids = payslip_line.search([('slip_id', '=', obj.id), ('salary_rule_id.parent_rule_id.id', '=', parent_line.salary_rule_id.id )])
        res = line_ids and line_ids[0] or False

        return res
    
    def _get_format(self,chiffre):
        chiffre = '{:20,.2f}'.format(chiffre)
        if (chiffre!=0):
            a=str(chiffre)
            a = a.replace(',','')
            b=a.split('.')
            c=b[0]
            d=b[1]
            e=c[::-1]
            i=0
            j=3
            f=''
            while(len(e[i:j])>0):
                if (len(e[i:j])>=3):
                    f+=e[i:j]+' '
                elif (len(e[i:j])<3):
                    f+=e[i:j]
                i+=3
                j+=3
                    
            g=f[::-1]+','+d
            return g
        else : return '0,0'

    @api.multi
    def render_html(self, docids, data=None):
        #=======================================================================
        # self.model = self.env.context.get('active_model')
        # docs = self.env[self.model].browse(self.env.context.get('active_ids', []))
        #=======================================================================
        
        docargs = {
            'doc_ids': docids,
            'doc_model': 'hr.payslip',
            'docs': self.env['hr.payslip'].browse(docids),
            'get_total_by_rule_category': self._get_total_by_rule_category,
            'get_employe_line': self._get_employe_line,
            'get_format': self._get_format,
            'data': data,
        }
        return self.env['report'].render('gestion_de_paie.report_paie', docargs)

     

    
    
