# -*- coding: utf-8 -*-

from odoo import fields, models, api
from collections import namedtuple
from odoo.exceptions import UserError
from odoo.tools.float_utils import float_compare
import re

# mapping invoice type to journal type
TYPE2JOURNAL = {
    'out_invoice': 'sale',
    'in_invoice': 'purchase',
    'out_refund': 'sale',
    'in_refund': 'purchase',
}


# Bugget Expense Report
class Bex(models.Model):
    _name = 'budget.expense.report'
    _inherit = ['mail.thread']
    _order = "date desc, id desc"
    _description = "Budget Expense Report"
    
    @api.multi
    def _compute_invoice_ids(self):
        for bex in self:
            invoice_ids = self.env['account.invoice'].search([('purchase_id', '=', self.breq_id.id)])
            if invoice_ids:
                bex.invoice_ids = invoice_ids
                bex.invoice_ids_count = len(invoice_ids)

    @api.depends('taux_change', 'amount_untaxed_bex')
    def _compute_amount_ht_ariary(self):
        for order in self:
            order.amount_total_ariary = order.taux_change * order.amount_untaxed_bex
            
    amount_total_ariary = fields.Float(string='Montant HT (Ar)', compute='_compute_amount_ht_ariary')
    
    be_lie_count = fields.Integer(compute='_compute_be_lie')
    be_ids = fields.One2many('stock.picking', string="be_ids", compute='_compute_be_lie')
    
    invoice_ids_count = fields.Integer(compute='_compute_invoice_ids')
    invoice_ids = fields.One2many('account.invoice', string="Invoices", compute='_compute_invoice_ids')
    
    def calculer_prix_revient(self):
        if self.taux_change == 0.0:
            raise UserError(u'Le taux de change doit être non nul')
        purchase_obj = self.env['purchase.order']
        purchase_line_obj = self.env['purchase.order.line']
        bex_obj = self.env['budget.expense.report']
        bex_line_obj = self.env['bex.line']
        
        if self.purchase_type == 'purchase_import':
            
            breq_transport = purchase_obj.search(['&', ('parents_ids', '=', self.breq_id.id), ('service_type', '=', 'transport')])
            breq_assurance = purchase_obj.search(['&', ('parents_ids', '=', self.breq_id.id), ('service_type', '=', 'assurance')])
            breq_additionnel = purchase_obj.search(['&', ('parents_ids', '=', self.breq_id.id), ('service_type', '=', 'additionel')])
            breq_droit_douane = purchase_obj.search(['&', ('parents_ids', '=', self.breq_id.id), ('service_type', '=', 'douane')], limit=1)
            
            bex_transport = bex_obj.search([('breq_id', 'in', tuple([breq.id for breq in breq_transport]))])
            bex_assurance = bex_obj.search([('breq_id', 'in', tuple([breq.id for breq in breq_assurance]))])
            bex_additionnel = bex_obj.search([('breq_id', 'in', tuple([breq.id for breq in breq_additionnel]))])
            bex_droit_douane = bex_obj.search([('breq_id', 'in', tuple([breq.id for breq in breq_droit_douane]))])

            total_assurance_fret = sum(x.amount_untaxed_bex for x in bex_transport) + sum(x.amount_untaxed_bex for x in bex_assurance)
            cLocTotal = sum(x.amount_untaxed_bex for x in bex_additionnel)
            fob_total = sum(line.qty_done * line.price_unit for line in self.bex_lines)
            caf_total = (fob_total + total_assurance_fret) * self.taux_change
            
            for line in self.bex_lines:
                if fob_total == 0.0:
                    raise UserError(u'FOB total ne devrait pas être nulle')
                elif line.qty_done <= 0.0:
                    raise UserError(u'La quantité des articles devrait être un nombre positif et non nul')
                else:
                    bex_line_id = bex_line_obj.search([('bex_id', '=', bex_droit_douane.id), ('purchase_line_id.purchase_line_id', '=', line.purchase_line_id.id)], limit=1)
                    droit_douane = bex_line_id.montant_realise
                    line.prix_unitaire = (((caf_total + cLocTotal) * ((line.qty_done * line.price_unit) / fob_total)) + droit_douane) / (line.qty_done)
    
    @api.multi
    def _compute_be_lie(self):
        for bex in self:
            be_ids = self.env['stock.picking'].search([('bex_id', '=', bex.id)])
            if be_ids:
                bex.be_ids = be_ids
                bex.be_lie_count = len(be_ids)
    
    def get_number(self, chaine, prefixe):
        if not chaine or chaine == '':
            raise UserError(u"Caractère en paramètre vide pour la fonction get_number()")
        liste_entier = re.findall("\d+", chaine)
        res = prefixe + '' + str(liste_entier[len(liste_entier) - 1])
        return res
                
    def _name_change(self):
        for bex in self :
            if bex.origin:
                res = re.findall("\d+", bex.origin)
                longeur_res = len(res)
                res_final = res[longeur_res - 1]
                bex.name = "BEX" + "".join(res_final)
    
    @api.multi
    def action_view_be(self):
        
        action = self.env.ref('stock.action_picking_tree')
        result = action.read()[0]

        result.pop('id', None)
        result['context'] = {}
        pick_ids = sum([bex.be_ids.ids for bex in self], [])
        if len(pick_ids) > 1:
            result['domain'] = "[('id','in',[" + ','.join(map(str, pick_ids)) + "])]"
        elif len(pick_ids) == 1:
            res = self.env.ref('stock_heri.view_picking_form_be', False)
            result['views'] = [(res and res.id or False, 'form')]
            result['res_id'] = pick_ids and pick_ids[0] or False
        return result
    
    @api.multi
    def action_view_invoices(self):
        action = self.env.ref('account.action_invoice_tree2')
        result = action.read()[0]

        invoice_ids = self.mapped('invoice_ids')
        if len(invoice_ids) > 1:
            result['domain'] = [('id', 'in', invoice_ids.ids)]
        elif len(invoice_ids) == 1:
            result['views'] = [(self.env.ref('account.invoice_supplier_form').id, 'form')]
            result['res_id'] = invoice_ids.id
        return result
        
    @api.depends('remise', 'bex_lines', 'bex_lines.qty_done', 'bex_lines.taxes_id', 'bex_lines.prix_unitaire')
    def _amount_all(self):
        for bex in self:
            amount_untaxed_bex = 0.0
            amount_taxed_bex = 0.0
            remise = 0.0
            if bex.remise:
                remise = bex.remise
                
            for line in bex.bex_lines:
                amount_untaxed_bex += line.montant_realise
                amount_taxed_bex += line.montant_realise_taxe
                
            amount_untaxed_bex = amount_untaxed_bex * (1 - (remise / 100))
            amount_taxed_bex = amount_taxed_bex * (1 - (remise / 100))
            
            bex.update({
                'amount_untaxed_bex': amount_untaxed_bex,
                'amount_tax_bex': amount_taxed_bex - amount_untaxed_bex,
                'amount_total_bex': amount_taxed_bex,
                })
            
    @api.depends('amount_total_en_ar')
    def _amount_en_ar(self):
        for res in self:
            res.amount_total_en_ar = res.amount_untaxed_en_ar - res.amount_tax_en_ar
    
    def attente_hierarchie(self):
        self.state = 'attente_hierarchie'
        self.change_state_date = fields.Datetime.now()
        
    def annuler_attente_hierarchie(self):
        self.state = 'draft'
        self.change_state_date = fields.Datetime.now()
        
    def hierarchie_ok(self):
        self.state = 'hierarchie_ok'
        self.change_state_date = fields.Datetime.now()
        
    def annuler_hierarchie_ok(self):
        self.state = 'attente_hierarchie'
        self.change_state_date = fields.Datetime.now()

    def annuler_comptabiliser(self):
        self.state = 'hierarchie_ok'
        self.change_state_date = fields.Datetime.now()
            
    def comptabiliser(self):
        # if self.breq_id and self.breq_id.purchase_type == 'purchase_import' and self.state == 'hierarchie_ok' and self.amount_untaxed_en_ar == 0.0:
            # raise UserError("Merci de remplir le Montant Hors Taxes en Ar!")

        if self.breq_id and self.breq_id.purchase_type != 'purchase_not_stored':
            self.create_be()
        self.create_invoice()
        self.state = 'comptabilise'
    
    def _prepare_invoice_line_from_bex_line(self, invoice, line):
        invoice_line = self.env['account.invoice.line']
        journal_id = invoice.journal_id
        price_unit = line.prix_unitaire
        if self.purchase_type == 'purchase_import':
            price_unit = line.price_unit
            
        data = {
            'invoice_id': invoice.id,
            'purchase_line_id': line.purchase_line_id.id,
            'name': line.bex_id.name + ': ' + line.purchase_line_id.name,
            'origin': line.breq_id.name + ', ' + line.bex_id.name,
            'uom_id': line.purchase_line_id.product_uom.id,
            'product_id': line.product_id.id,
            'account_id': invoice_line.with_context({'journal_id': journal_id.id, 'type': 'in_invoice'})._default_account(),
            'price_unit': self.currency_id.compute(price_unit, invoice.currency_id, round=False),
            'quantity': line.qty_done,
            'discount': 0.0,
            'account_analytic_id': line.purchase_line_id.account_analytic_id.id,
            'analytic_tag_ids': line.purchase_line_id.analytic_tag_ids.ids,
            #'invoice_line_tax_ids': line.purchase_line_id.taxes_id.ids
        }
        
        return data
    
    def create_invoice(self):
        self.ensure_one()
        Invoice = self.env['account.invoice']
        Invoice_lines = self.env['account.invoice.line']
        inv_types = ['in_invoice']
        domain = [
            ('type', 'in', filter(None, map(TYPE2JOURNAL.get, inv_types))),
            ('company_id', '=', self.env.user.company_id.id),
        ]
        journal_id = self.env['account.journal'].search(domain, limit=1)
        
        invoice_data = {
                    'partner_id': self.partner_id.id,
                    'type': 'in_invoice',
                    'currency_id': self.currency_id.id,
                    'purchase_id': self.breq_id.id,
                    'origin': self.name,
                    'journal_id': journal_id.id
                    }
        invoice = Invoice.create(invoice_data)
        for line in self.bex_lines:
            vals = self._prepare_invoice_line_from_bex_line(invoice, line)
            invoice_line = Invoice_lines.create(vals)
            taxes = line.purchase_line_id.taxes_id
            invoice_line_tax_ids = self.breq_id.fiscal_position_id.map_tax(taxes)
            invoice_line.invoice_line_tax_ids = invoice_line_tax_ids
        invoice._onchange_invoice_line_ids()
        
            #invoice_line._set_additional_fields(invoice)
            #invoice_line._compute_price()
        #invoice._compute_amount()
            
    @api.one
    def _get_is_manager(self):
        self.is_manager = False
        current_employee_id = self.env['hr.employee'].search([('user_id', '=', self.env.uid)]).id
        manager_id = self.employee_id.coach_id.id
        if current_employee_id == manager_id:
            self.is_manager = True
    
    @api.one
    def _get_is_creator(self):
        self.is_creator = False
        current_employee_id = self.env['hr.employee'].search([('user_id', '=', self.env.uid)], limit=1).id
        employee_id = self.employee_id.id
        if current_employee_id == employee_id:
            self.is_creator = True
            
    def _currency_en_ar(self):
        for bex in self:
            bex.currency_en_ar = bex.env.ref('base.MGA').id
        
    name = fields.Char(compute="_name_change", readonly=True)
    breq_id = fields.Many2one('purchase.order', string=u"Budget Request lié", readonly=True)
    state = fields.Selection([
        ('draft', 'Nouveau'), ('cancel', 'Cancelled'),
        ('attente_hierarchie', 'Avis supérieur hierarchique'),
        ('hierarchie_ok', 'Validation supérieur hierarchique'), 
        ('comptabilise', 'Comptabilisé')], string='Statut', track_visibility='onchange',
        help="Etat", default='draft')
    partner_id = fields.Many2one('res.partner', related='breq_id.partner_id', readonly=True)
    
    location_id = fields.Many2one('stock.location', "Source Location Zone", readonly=True)
    location_dest_id = fields.Many2one('stock.location', "Source Location Zone", readonly=True)
        
    purchase_type = fields.Selection(related='breq_id.purchase_type')
    employee_id = fields.Many2one('hr.employee', related='breq_id.employee_id', readonly=True)
    department_id = fields.Many2one('hr.department', related='breq_id.department_id', readonly=True)
    objet = fields.Text(related='breq_id.objet', readonly=True)
    section = fields.Char(related='breq_id.section', readonly=True)
    nature = fields.Char(related='breq_id.nature', readonly=True)
    manager_id = fields.Many2one('hr.employee', related='breq_id.manager_id', readonly=True)
    is_manager = fields.Boolean(compute="_get_is_manager", string='Est un manager')
    currency_id = fields.Many2one('res.currency', related='breq_id.currency_id', string='Devise', readonly=True)
    currency_en_ar = fields.Many2one('res.currency', compute="_currency_en_ar", readonly=True)
    is_creator = fields.Boolean(compute="_get_is_creator", string='Est le demandeur')
    date = fields.Datetime('Date', default=fields.Datetime.now, readonly=True)
    origin = fields.Char('Document d\'origine', readonly=True)
    
    change_state_date = fields.Datetime(string="Date changement d\'état", readonly=True, help="Date du dernier changement d\'état.")
    
    budgetise = fields.Float("Budgetisé")
    cumul = fields.Float("Cumul Real. + ENgag.")
    solde = fields.Float("Solde de budget")
    journal_id = fields.Many2one('account.journal', string='Mode de paiement', domain=[('type', 'in', ('bank', 'cash'))])
    
    amount_untaxed_bex = fields.Float(compute='_amount_all', string='Montant HT', readonly=True, store=True)
    amount_tax_bex = fields.Float(compute='_amount_all', string='Taxes', readonly=True, store=True)
    amount_total_bex = fields.Float(compute='_amount_all', string='Total', readonly=True, store=True)
    
    # Budget request
    amount_untaxed_breq = fields.Float('Montant HT', readonly=True)
    amount_tax_breq = fields.Float('Taxes', readonly=True)
    amount_total_breq = fields.Float('Total', readonly=True)
    
    # Budget expenses Montant en Ariary
    amount_untaxed_en_ar = fields.Float('Montant HT')
    amount_tax_en_ar = fields.Float('Taxes')
    amount_total_en_ar = fields.Float(compute='_amount_en_ar', string='Total')
    
    observation = fields.Text("Obsevations")
    solde_rembourser = fields.Monetary('Solde à rembourser/payer')
    
    bex_lines = fields.One2many('bex.line', 'bex_id', string="BEX LINES")
    remise = fields.Float('Remise (%)')
    
    move_type = fields.Selection([
        ('direct', 'Partial'), ('one', 'All at once')], 'Delivery Type',
        default='direct',
        states={'done': [('readonly', True)], 'cancel': [('readonly', True)]},
        help="It specifies goods to be deliver partially or all at once")
    picking_type_id = fields.Many2one('stock.picking.type', 'Type de préparation', readonly=True)
    company_id = fields.Many2one('res.company', 'Company', readonly=True)
    group_id = fields.Many2one('procurement.group', 'Procurement Group', readonly=True)
    
    taux_change = fields.Float(string='Taux de change', default=1.0)
    
    
    # Fonction dans achat
    @api.model
    def _prepare_picking(self):
        if not self.group_id:
            self.group_id = self.group_id.create({
                'name': self.origin,
                'partner_id': self.partner_id.id
            })
        if not self.partner_id.property_stock_supplier.id:
            raise UserError(_("You must set a Vendor Location for this partner %s") % self.partner_id.name)
        return {
            'picking_type_id': self.picking_type_id.id,
            'partner_id': self.partner_id.id,
            'bex_id': self.id,
            'date': self.date,
            'origin': self.name,
            'location_dest_id': self.picking_type_id.default_location_dest_id.id,
            'location_id': self.partner_id.property_stock_supplier.id,
            'company_id': self.company_id.id,
            'mouvement_type': 'be',
            'name': self.get_number(self.name, 'BE'),
        }
        
    @api.multi
    def create_be(self):
        StockPicking = self.env['stock.picking']
        for bex in self:
            res = bex._prepare_picking()
            picking = StockPicking.create(res)
            moves = bex.bex_lines._create_stock_moves(picking)
            moves = moves.filtered(lambda x: x.state not in ('done', 'cancel')).action_confirm()
            moves.force_assign()
            picking.message_post_with_view('mail.message_origin_link',
                values={'self': picking, 'origin': bex},
                subtype_id=self.env.ref('mail.mt_note').id)
        return True


class BexLine(models.Model):
    _name = "bex.line"
    
    name = fields.Char('Désignation')
    bex_id = fields.Many2one('budget.expense.report', u'Référence Bex')
    product_id = fields.Many2one('product.product', 'Article')
    product_qty = fields.Float('Qté BReq', readonly=True)
    qty_done = fields.Float('Qté Reçue')
    prix_unitaire = fields.Float('PU Bex')
    montant_br = fields.Float('Montant BReq HT', readonly=True)
    montant_realise = fields.Float(compute='_compute_amount', string='Montant Bex HT', readonly=True, store=True)
    montant_realise_taxe = fields.Float(compute='_compute_amount', string='Montant Bex TTC', readonly=True, store=True)
    taxes_id = fields.Many2many('account.tax', string='Taxes', domain=['|', ('active', '=', False), ('active', '=', True)])
    price_unit = fields.Float('PU BReq')
    
    purchase_type = fields.Selection([
        ('purchase_stored', 'Achats locaux stockés'),
        ('purchase_not_stored', 'Achats locaux non stockés'),
        ('purchase_import', 'Achats à l\'importation')
    ], string='Type d\'achat')
    
    breq_id = fields.Many2one('purchase.order', string='ID Breq')
    purchase_line_id = fields.Many2one('purchase.order.line', string='ID ligne de commande')
    product_uom = fields.Many2one('product.uom', string='Unité de mesure')
    
    @api.depends('qty_done', 'prix_unitaire', 'taxes_id')
    def _compute_amount(self):
        for line in self:
            if line.qty_done > line.product_qty or line.qty_done < 0.0:
                raise UserError(u'La quantité reçue doit être inférieur ou égale à la quantité du BReq et positive')
            
#             taxes = line.taxes_id.compute_all(line.prix_unitaire, line.bex_id.currency_id, line.qty_done, product=line.product_id, partner=False)
#             line.update({
#                  'montant_realise': taxes['total_excluded'],
#                  'montant_realise_taxe': taxes['total_included'],
#             })
            
            line.montant_realise = line.qty_done * line.prix_unitaire
            
    @api.multi
    def _create_stock_moves(self, picking):
        moves = self.env['stock.move']
        done = self.env['stock.move'].browse()
        for line in self:
            if line.product_id.type not in ['product', 'consu']:
                continue
            template = {
                'name': line.product_id.name or '',
                'product_id': line.product_id.id,
                'product_uom': line.purchase_line_id.product_uom.id,
                'product_uom_qty': line.qty_done,
                'date': line.bex_id.date,
                'date_expected': line.purchase_line_id.date_planned,
                'location_id': line.bex_id.location_id.id,
                'location_dest_id': line.bex_id.location_dest_id.id,
                'picking_id': picking.id,
                'partner_id': line.bex_id.breq_id.dest_address_id.id,
                'move_dest_id': False,
                'state': 'draft',
                'purchase_line_id': line.purchase_line_id.id,
                'company_id': line.bex_id.breq_id.company_id.id,
                'price_unit': line.prix_unitaire,
                'picking_type_id': line.bex_id.picking_type_id.id,
                'group_id': line.bex_id.group_id.id,
                'procurement_id': False,
                'origin': line.bex_id.name,
                'route_ids': line.bex_id.breq_id.picking_type_id.warehouse_id and [(6, 0, [x.id for x in line.bex_id.breq_id.picking_type_id.warehouse_id.route_ids])] or [],
                'warehouse_id': line.bex_id.breq_id.picking_type_id.warehouse_id.id,
            }
            done += moves.create(template)
        return done