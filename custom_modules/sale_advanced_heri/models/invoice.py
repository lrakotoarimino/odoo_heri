# -*- coding: utf-8 -*-
import json

from datetime import datetime
from dateutil import relativedelta

from odoo import models, fields, api, _
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT, float_is_zero, amount_to_text

from odoo.exceptions import UserError, ValidationError

import odoo.addons.decimal_precision as dp


# mapping invoice type to journal type
TYPE2JOURNAL = {
    'out_invoice': 'sale',
    'in_invoice': 'purchase',
    'out_refund': 'sale',
    'in_refund': 'purchase',
}

INVOICETYPE2CODE = {
    'rental': 'RED',
    'sale': 'VTE',
    'loss': 'PRT',
    'refund': 'AVR',
}


to_19_fr = (u'zéro', 'un', 'deux', 'trois', 'quatre', 'cinq', 'six',
          'sept', 'huit', 'neuf', 'dix', 'onze', 'douze', 'treize',
          'quatorze', 'quinze', 'seize', 'dix-sept', 'dix-huit', 'dix-neuf')
tens_fr = ('vingt', 'trente', 'quarante', 'Cinquante', 'Soixante', 'Soixante-dix', 'Quatre-vingts', 'Quatre-vingt Dix')
denom_fr = ('',
          'Mille', 'Millions', 'Milliards', 'Billions', 'Quadrillions',
          'Quintillion', 'Sextillion', 'Septillion', 'Octillion', 'Nonillion',
          'Décillion', 'Undecillion', 'Duodecillion', 'Tredecillion', 'Quattuordecillion',
          'Sexdecillion', 'Septendecillion', 'Octodecillion', 'Icosillion', 'Vigintillion')

def _convert_nn_fr(val):
    """ convert a value < 100 to French
    """
    if val < 20:
        return to_19_fr[val]
    for (dcap, dval) in ((k, 20 + (10 * v)) for (v, k) in enumerate(tens_fr)):
        if dval + 10 > val:
            if val % 10:
                if dval == 70 or dval == 90:
                    return tens_fr[dval / 10 - 3] + '-' + to_19_fr[val % 10 + 10]
                else:
                    return dcap + '-' + to_19_fr[val % 10]
            return dcap

def _convert_nnn_fr(val):
    """ convert a value < 1000 to french
    
        special cased because it is the level that kicks 
        off the < 100 special case.  The rest are more general.  This also allows you to
        get strings in the form of 'forty-five hundred' if called directly.
    """
    word = ''
    (mod, rem) = (val % 100, val // 100)
    if rem > 0:
        if rem == 1:
            word = 'Cent'
        else:
            word = to_19_fr[rem] + ' Cent'
        if mod > 0:
            word += ' '
    if mod > 0:
        word += _convert_nn_fr(mod)
    return word

def french_number(val):
    if val < 100:
        return _convert_nn_fr(val)
    if val < 1000:
        return _convert_nnn_fr(val)
    for (didx, dval) in ((v - 1, 1000 ** v) for v in range(len(denom_fr))):
        if dval > val:
            mod = 1000 ** didx
            l = val // mod
            r = val - (l * mod)
            if l == 1:
                ret = denom_fr[didx]
            else:
                ret = _convert_nnn_fr(l) + ' ' + denom_fr[didx]
            if r > 0:
                ret = ret + ', ' + french_number(r)
            return ret

def amount_to_text(numbers, currency):
    number = '%.2f' % numbers
    units_name = currency
    liste = str(number).split('.')
    start_word = french_number(abs(int(liste[0])))
    end_word = ''
    str_dec = liste[1]
    if int(liste[1]) != 0:
        end_word = french_number(int(str_dec))
        str_dec_new = str(int(str_dec))
        nbr_zero = len(str_dec) - len(str_dec_new)
        if nbr_zero > 0:
            for i in range(nbr_zero):
                end_word = to_19_fr[0] + ' ' + end_word
    
    result = start_word.capitalize() + ' ' + units_name + ' ' + end_word
    final_result = result.strip()
    return final_result


class AccountInvoice(models.Model):
    _inherit = "account.invoice"
    
    # redefinition
    @api.one
    @api.depends('payment_move_line_ids.amount_residual')
    def _get_payment_info_JSON(self):
        self.payments_widget = json.dumps(False)
        if self.payment_move_line_ids:
            info = {'title': _('Less Payment'), 'outstanding': False, 'content': []}
            currency_id = self.currency_id
            
            # redefinition
            advance = 0.0
            
            for payment in self.payment_move_line_ids:
                payment_currency_id = False
                if self.type in ('out_invoice', 'in_refund'):
                    amount = sum([p.amount for p in payment.matched_debit_ids if p.debit_move_id in self.move_id.line_ids])
                    amount_currency = sum([p.amount_currency for p in payment.matched_debit_ids if p.debit_move_id in self.move_id.line_ids])
                    if payment.matched_debit_ids:
                        payment_currency_id = all([p.currency_id == payment.matched_debit_ids[0].currency_id for p in payment.matched_debit_ids]) and payment.matched_debit_ids[0].currency_id or False
                elif self.type in ('in_invoice', 'out_refund'):
                    amount = sum([p.amount for p in payment.matched_credit_ids if p.credit_move_id in self.move_id.line_ids])
                    amount_currency = sum([p.amount_currency for p in payment.matched_credit_ids if p.credit_move_id in self.move_id.line_ids])
                    if payment.matched_credit_ids:
                        payment_currency_id = all([p.currency_id == payment.matched_credit_ids[0].currency_id for p in payment.matched_credit_ids]) and payment.matched_credit_ids[0].currency_id or False
                # get the payment value in invoice currency
                if payment_currency_id and payment_currency_id == self.currency_id:
                    amount_to_show = amount_currency
                else:
                    amount_to_show = payment.company_id.currency_id.with_context(date=payment.date).compute(amount, self.currency_id)
                if float_is_zero(amount_to_show, precision_rounding=self.currency_id.rounding):
                    continue
                payment_ref = payment.move_id.name
                if payment.move_id.ref:
                    payment_ref += ' (' + payment.move_id.ref + ')'
                info['content'].append({
                    'name': payment.name,
                    'journal_name': payment.journal_id.name,
                    'amount': amount_to_show,
                    'currency': currency_id.symbol,
                    'digits': [69, currency_id.decimal_places],
                    'position': currency_id.position,
                    'date': payment.date,
                    'payment_id': payment.id,
                    'move_id': payment.move_id.id,
                    'ref': payment_ref,
                })
                
                # redefinition
                advance += amount_to_show
            self.advance = advance
            
            self.payments_widget = json.dumps(info)
    
    @api.model
    def _default_account_type(self):
        if self._context.get('invoice_type', False):
            return self._context.get('invoice_type', False)
        
    @api.model
    def _default_journal(self):
        if self._context.get('default_journal_id', False):
            return self.env['account.journal'].browse(self._context.get('default_journal_id'))
        inv_type = self._context.get('type', 'out_invoice')
        inv_types = inv_type if isinstance(inv_type, list) else [inv_type]
        company_id = self._context.get('company_id', self.env.user.company_id.id)
        domain = [
            ('type', 'in', filter(None, map(TYPE2JOURNAL.get, inv_types))),
            ('company_id', '=', company_id),
        ]
        
        # redefinition
        if self._context.get('invoice_type', False):
            invoice_type = self._context.get('invoice_type')
            if invoice_type in ('rental', 'sale', 'loss', 'refund'):
                domain.append(('code', '=', INVOICETYPE2CODE[invoice_type]))
                if not self.env['account.journal'].search(domain, limit=1):
                    raise UserError(_("Configuration error!\nCould not find account journal with code %s") % INVOICETYPE2CODE[invoice_type])
        return self.env['account.journal'].search(domain, limit=1)
    
    @api.onchange('kiosk_id')
    def _onchange_kiosk_id(self):
        if not self.kiosk_id:
            self.partner_id = False
            return
          
        partner_id = self.env['res.partner'].search([('kiosk_id', '=', self.kiosk_id.id)], limit=1)
        if partner_id:
            self.partner_id = partner_id.id
        else:
            self.partner_id = False
      
    @api.onchange('partner_id', 'company_id')
    def _onchange_partner_id(self):
        res = super(AccountInvoice, self)._onchange_partner_id()
        if self.partner_id and self.partner_id.kiosk_id:
            self.kiosk_id = self.partner_id.kiosk_id.id
        return res
    
    @api.onchange('date_start', 'date_end')
    def _onchange_billing_date(self):
        if self.date_start and self.date_end:
            if self.date_start >= self.date_end:
                return {
                'warning': {'title': _('Error!'), 'message': _('The start date must be strictly less than the end date'), },
                'value': {'date_start': False, 'date_end': False, }
                }
    
    @api.one
    @api.depends('amount_total', 'residual')
    def _compute_amount_in_word(self):
        if not self.currency_id.full_name:
            raise UserError(_("Error!\nPlease complete monetary name in currency configuration"))
        monetary = self.currency_id.full_name
        amount = self.amount_total
        if self.residual != 0.0:
            amount = self.residual
        self.amount_in_word = amount_to_text(amount, monetary)
                
    journal_id = fields.Many2one('account.journal', string='Journal',
        required=True, readonly=True, states={'draft': [('readonly', False)]},
        default=_default_journal,
        domain="[('type', 'in', {'out_invoice': ['sale'], 'out_refund': ['sale'], 'in_refund': ['purchase'], 'in_invoice': ['purchase']}.get(type, [])), ('company_id', '=', company_id)]")
    kiosk_id = fields.Many2one('stock.location', string='Kiosk *')
    date_start = fields.Datetime(string='Start date')
    date_end = fields.Datetime(string='End date')
    invoice_type = fields.Selection([('rental', 'Rental'), ('sale', 'Sale'), ('loss', 'Loss'), ('refund', 'Refund')], string="Type invoice", default=_default_account_type)
    
    kiosk_id = fields.Many2one('stock.location', string='Kiosk *')
    date_start = fields.Date(string='Billing start date', default=str(datetime.now() + relativedelta.relativedelta(months=-2, day=26))[:10])
    date_end = fields.Date(string='Billing end date', default=str(datetime.now() + relativedelta.relativedelta(months=-1, day=25))[:10])
    
    state = fields.Selection([
            ('draft', 'Draft'),
            ('proforma2', 'Ouvertes'),
            ('open', u'Validé'),
            ('partially_paid', u'Partiellement payé'),
            ('paid', 'Paid'),
            ('cancel', 'Cancelled'),
        ], string='Status', index=True, readonly=True, default='draft',
        track_visibility='onchange', copy=False,
        help=" * The 'Draft' status is used when a user is encoding a new and unconfirmed Invoice.\n"
             " * The 'Pro-forma' status is used when the invoice does not have an invoice number.\n"
             " * The 'Open' status is used when user creates invoice, an invoice number is generated. It stays in the open status till the user pays the invoice.\n"
             " * The 'Paid' status is set automatically when the invoice is paid. Its related journal entries may or may not be reconciled.\n"
             " * The 'Cancelled' status is used when user cancel invoice.")
    
    amount_in_word = fields.Char(string='Amount in word', store=True, readonly=True, compute='_compute_amount_in_word')
    advance = fields.Monetary(string='Advance', compute='_get_payment_info_JSON', store=True)
    stock_scrap_ids = fields.Many2many(string="Scraps", comodel_name="stock.scrap", copy=False)
    
    def get_move_lines(self, type_move='in', number_days_max=0.0):
        if not self.kiosk_id:
            UserError(_('Please specify the kiosk'))
        kiosk_id = self.kiosk_id.id
        StockMove = self.env['stock.move']
        AccountInvoiceLine = self.env['account.invoice.line']
                
        date0, date1 = datetime.strptime(self.date_start, DEFAULT_SERVER_DATE_FORMAT), datetime.strptime(self.date_end, DEFAULT_SERVER_DATE_FORMAT)
        date_start, date_end = fields.Date.to_string(date0.replace(hour=23, minute=59, second=59)), fields.Date.to_string(date1.replace(hour=23, minute=59, second=59))
        domain = [('date', '>=', date_start), ('date', '<=', date_end)]
        sign = 1
        
        if type_move == 'out':
            domain.append(('location_id', '=', kiosk_id))
            moves = StockMove.search(domain, order='product_id, date desc')
            sign = -1
        else:
            domain.append(('location_dest_id', '=', kiosk_id))
            moves = StockMove.search(domain, order='product_id, date desc')
        
        todo_moves = []
        for move in moves:
            name = move.product_id.name
            d1 = datetime.strptime(move.date, DEFAULT_SERVER_DATETIME_FORMAT).date()
            d2 = date1.date()
            delta = d2 - d1
            
            account_id = False
            account = AccountInvoiceLine.get_invoice_line_account(self.type, move.product_id, self.fiscal_position_id, self.company_id)
            if account:
                account_id = account.id
            
            if move.product_id.description_sale:
                name += '\n%s' % (move.product_id.description_sale)
                
            vals = {'date': move.date,
                    'product_id': move.product_id.id,
                    'name': name,
                    'account_id': account_id,
                    'uom_id': move.product_id.uom_id.id,
                    'quantity': sign * move.product_uom_qty,
                    'number_days': number_days_max < delta.days + 1 and number_days_max or delta.days + 1,
                    'price_unit': move.product_id.rental_price,
                    'invoice_id': self.id,
                    }
            todo_moves.append(vals)
        
        return todo_moves
            
    def get_invoice_line(self):
        self.ensure_one()
        self.invoice_line_ids.unlink()
        Inventory = self.env['stock.inventory']
        AccountInvoiceLine = self.env['account.invoice.line']
        BillingTableLine = self.env['billing.table.line']
        
        date_start = datetime.strptime(self.date_start, DEFAULT_SERVER_DATE_FORMAT)
        date_end = datetime.strptime(self.date_end, DEFAULT_SERVER_DATE_FORMAT)
        
        if not self.kiosk_id.billing_table_id:
                raise UserError(_('Error!/nNo billing table created for this kiosk'))
        table_id = self.kiosk_id.billing_table_id
        current_month = date_end.month
        table_line = BillingTableLine.search([('table_id', '=', table_id.id), ('month', '=', current_month)], limit=1)
        if not table_line:
            raise UserError(_('Error configuration!/nPlease configure billing table for this current month'))
        number_days = table_line.number_days
        
        # Dates for inventory day
        date1 = fields.Date.to_string(date_start.replace(hour=0, minute=0, second=1))
        date2 = fields.Date.to_string(date_start.replace(hour=23, minute=59, second=59))
        domain = [('state', 'in', ('confirm', 'done')), ('location_id', '=', self.kiosk_id.id), ('date', '>=', date1), ('date', '<=', date2)]
        inventory = Inventory.search(domain, order='date desc', limit=1)
        if not inventory:
            raise UserError(_('Error!/nNo inventory created for this kiosk'))

        invoice_type = self.type
        fpos = self.fiscal_position_id
        company = self.company_id
        
        # Get stock move
        moves = []
        moves += self.get_move_lines('in', number_days)
        moves += self.get_move_lines('out', number_days)
        for move in moves:
            AccountInvoiceLine.create(move)
        
        # Get stock inventory
        vals = {}
        line_ids = inventory.line_ids.filtered(lambda l: l.product_id.fee_type == 'variable')
        for line in line_ids:
            if line.state == 'confirm':
                qty = line.theoretical_qty
            elif line.state == 'done':
                qty = line.product_qty
            
            product = line.product_id
            name = product.partner_ref
            if line.product_id.description_sale:
                name += '\n' + product.description_sale
            price = line.product_id.rental_price
            
            account_id = False
            account = AccountInvoiceLine.get_invoice_line_account(invoice_type, product, fpos, company)
            if account:
                account_id = account.id
            
            vals = {'date': line.inventory_id.date,
                    'product_id': product.id,
                    'name': name,
                    'account_id': account_id,
                    'uom_id': line.product_uom_id.id,
                    'quantity': qty,
                    'number_days': number_days,
                    'price_unit': price,
                    'invoice_id': self.id,
                    }
            AccountInvoiceLine.create(vals)
            
        # Fee rental fix
        product_fix_id = self.env['product.product'].browse(self.env.ref('sale_advanced_heri.product_product_0').id)
        account_id = False
        account = AccountInvoiceLine.get_invoice_line_account(invoice_type, product_fix_id, fpos, company)
        if account:
            account_id = account.id
        vals = {'date': inventory.date,
                'product_id': product_fix_id.id,
                'name': product_fix_id.name + ' ' + str(self.kiosk_id.name),
                'account_id': account_id,
                'uom_id': product_fix_id.uom_id.id,
                'quantity': 1.0,
                'number_days': 1.0,
                'price_unit': product_fix_id.rental_price,
                'invoice_id': self.id,
                }
        AccountInvoiceLine.create(vals)
        
        invoice_lines = AccountInvoiceLine.search([('invoice_id', '=', self.id)], order='product_id, date desc')
        sequence = 0
        for inv in invoice_lines:
            inv.write({'sequence': sequence})
            sequence += 1
            
    # redefinition
    @api.multi
    def _write(self, vals):
        pre_not_reconciled = self.filtered(lambda invoice: not invoice.reconciled)
        pre_reconciled = self - pre_not_reconciled
        res = super(AccountInvoice, self)._write(vals)
        reconciled = self.filtered(lambda invoice: invoice.reconciled)
        not_reconciled = self - reconciled
        
        # redefinition : consider the state partially paid
        (reconciled & pre_reconciled).filtered(lambda invoice: invoice.state in ('open', 'partially_paid')).action_invoice_paid()
        #
        
        (not_reconciled & pre_not_reconciled).filtered(lambda invoice: invoice.state == 'paid').action_invoice_re_open()
        return res
    
    # redefinition
    @api.multi
    def action_invoice_paid(self):
        # lots of duplicate calls to action_invoice_paid, so we remove those already paid
        to_pay_invoices = self.filtered(lambda inv: inv.state != 'paid')
        
        # redefinition : consider the state partially paid
        if to_pay_invoices.filtered(lambda inv: inv.state not in ('open', 'partially_paid')):
            raise UserError(_('Invoice must be validated in order to set it to register payment.'))
        #
        
        if to_pay_invoices.filtered(lambda inv: not inv.reconciled):
            raise UserError(_('You cannot pay an invoice which is partially paid. You need to reconcile payment entries first.'))
        return to_pay_invoices.write({'state': 'paid'})
    
    @api.multi
    def invoice_print_new(self):
        self.ensure_one()
        self.sent = True
        return self.env['report'].get_action(self, 'sale_advanced_heri.report_invoice_redevance')

    @api.multi
    def action_invoice_open(self):
        """ Pertes: If type is Loss, mark products as scrapped:
                - Create stock scrap
                - Validate it
        """
        res = super(AccountInvoice, self).action_invoice_open()
        for inv in self:
            if inv.invoice_type == 'loss':
                if not any([l.product_id.type in ['product', 'consu'] for l in inv.invoice_line_ids]):
                    raise exceptions.ValidationError(_("No consumables or storables products found."))

                # Create a stock scrap for each line and attach them to the invoice
                scraps = self.env['stock.scrap'].browse()
                for inv_line in inv.invoice_line_ids:
                    scraps += inv_line._create_stock_scrap()
                inv.stock_scrap_ids = scraps
        return res


    @api.multi
    def action_view_scrap(self):
        '''
        This function returns an action that display existing scraps
        of given account invoice ids. It can either be a in a list or in a form
        view, if there is only one scrap to show.
        '''
        action = self.env.ref('stock.action_stock_scrap').read()[0]

        scraps = self.mapped('stock_scrap_ids')
        if len(scraps) > 1:
            action['domain'] = [('id', 'in', scraps.ids)]
        elif scraps:
            action['views'] = [(self.env.ref('stock.stock_scrap_form_view').id, 'form')]
            action['res_id'] = scraps.id
        return action
            
    # redefinition
    @api.model
    def _prepare_refund(self, invoice, date_invoice=None, date=None, description=None, journal_id=None):
        values = super(AccountInvoice, self)._prepare_refund(invoice, date_invoice, date, description, journal_id)
        if invoice.type != 'out_invoice':
            return values
        
        values['kiosk_id'] = invoice.kiosk_id.id
        values['invoice_type'] = 'refund'
        
        company_id = self._context.get('company_id', self.env.user.company_id.id)
        domain = [('company_id', '=', company_id), ('code', '=', INVOICETYPE2CODE['refund'])]
        journal = self.env['account.journal'].search(domain, limit=1)
        if not journal:
            raise UserError(_("Configuration error!\nCould not find account journal with code %s") % INVOICETYPE2CODE['refund'])
        values['journal_id'] = journal.id
        
        return values
    
        
class AccountInvoiceLine(models.Model):
    _inherit = "account.invoice.line"
    
    # redefinition
    @api.one
    @api.depends('price_unit', 'discount', 'invoice_line_tax_ids', 'quantity',
    'product_id', 'invoice_id.partner_id', 'invoice_id.currency_id', 'invoice_id.company_id',
    'invoice_id.date_invoice', 'number_days')
    def _compute_price(self):
        currency = self.invoice_id and self.invoice_id.currency_id or None
        price = self.number_days * self.price_unit * (1 - (self.discount or 0.0) / 100.0)
        taxes = False
        if self.invoice_line_tax_ids:
            taxes = self.invoice_line_tax_ids.compute_all(price, currency, self.quantity, product=self.product_id, partner=self.invoice_id.partner_id)
        self.price_subtotal = price_subtotal_signed = taxes['total_excluded'] if taxes else self.quantity * price
        if self.invoice_id.currency_id and self.invoice_id.company_id and self.invoice_id.currency_id != self.invoice_id.company_id.currency_id:
            price_subtotal_signed = self.invoice_id.currency_id.with_context(date=self.invoice_id.date_invoice).compute(price_subtotal_signed, self.invoice_id.company_id.currency_id)
        sign = self.invoice_id.type in ['in_refund', 'out_refund'] and -1 or 1
        self.price_subtotal_signed = price_subtotal_signed * sign
    
    date = fields.Date(string='Date', default=fields.Date.context_today)
    number_days = fields.Float(string='Days', digits=dp.get_precision('Product Unit of Measure'), default=1.0)

    @api.model
    def _prepare_scrap(self):
        """
            Prepare value to create stock scrap
            :return dictionnary ready to be created
        """
        scrapped_location = self.env['ir.model.data'].xmlid_to_object('stock.stock_location_scrapped')

        return {
            'name': _('New'),
            'product_id': self.product_id.id,
            'product_uom_id': self.uom_id.id,
            'scrap_qty': self.quantity,
            'location_id': self.invoice_id.kiosk_id.id,
            'scrap_location_id': scrapped_location.id,
            'origin': unicode(self.invoice_id.number),
            'date_expected': self.invoice_id.date_invoice,
        }

    @api.multi
    def _create_stock_scrap(self):
        scraps = self.env['stock.scrap']
        done = scraps.browse()
        for line in self:
            val = line._prepare_scrap()
            done += scraps.create(val)
        return done


class AccountJournal(models.Model):
        _inherit = "account.journal"
        _sql_constraints = [('code_uniq', 'unique(code)', "A code must be unique !")]
        

class AccountPayment(models.Model):
    _inherit = "account.payment"

    payment_difference_handling = fields.Selection([('open', 'Set partially paid'), ('reconcile', 'Mark invoice as fully paid')], default='open', string="Payment Difference", copy=False)

    # redefinition
    @api.multi
    def post(self):
        """ Create the journal items for the payment and update the payment's state to 'posted'.
            A journal entry is created containing an item in the source liquidity account (selected journal's default_debit or default_credit)
            and another in the destination reconciliable account (see _compute_destination_account_id).
            If invoice_ids is not empty, there will be one reconciliable move line per invoice to reconcile with.
            If the payment is a transfer, a second journal entry is created in the destination journal to receive money from the transfer account.
        """
        for rec in self:

            if rec.state != 'draft':
                raise UserError(_("Only a draft payment can be posted. Trying to post a payment in state %s.") % rec.state)
            
            # redefinition : consider the state partially paid
            if any(inv.state not in ('open', 'partially_paid') for inv in rec.invoice_ids):
                raise ValidationError(_("The payment cannot be processed because the invoice is not open!"))
            #
            
            # Use the right sequence to set the name
            if rec.payment_type == 'transfer':
                sequence_code = 'account.payment.transfer'
            else:
                if rec.partner_type == 'customer':
                    if rec.payment_type == 'inbound':
                        sequence_code = 'account.payment.customer.invoice'
                    if rec.payment_type == 'outbound':
                        sequence_code = 'account.payment.customer.refund'
                if rec.partner_type == 'supplier':
                    if rec.payment_type == 'inbound':
                        sequence_code = 'account.payment.supplier.refund'
                    if rec.payment_type == 'outbound':
                        sequence_code = 'account.payment.supplier.invoice'
            rec.name = self.env['ir.sequence'].with_context(ir_sequence_date=rec.payment_date).next_by_code(sequence_code)

            # Create the journal entry
            amount = rec.amount * (rec.payment_type in ('outbound', 'transfer') and 1 or -1)
            move = rec._create_payment_entry(amount)

            # In case of a transfer, the first journal entry created debited the source liquidity account and credited
            # the transfer account. Now we debit the transfer account and credit the destination liquidity account.
            if rec.payment_type == 'transfer':
                transfer_credit_aml = move.line_ids.filtered(lambda r: r.account_id == rec.company_id.transfer_account_id)
                transfer_debit_aml = rec._create_transfer_entry(amount)
                (transfer_credit_aml + transfer_debit_aml).reconcile()

            rec.write({'state': 'posted', 'move_name': move.name})
            
    # redefinition
    def _create_payment_entry(self, amount):
        res = super(AccountPayment, self)._create_payment_entry(amount)
        
        # redefinition : consider the state partially paid
        if self.payment_difference_handling == 'open' and self.payment_difference:
            self.invoice_ids.write({'state': 'partially_paid'})
        #
        
        return res