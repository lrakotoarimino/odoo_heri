# -*- coding: utf-8 -*-

from datetime import datetime

from odoo import models, fields, api, _
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT

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
}


class AccountInvoice(models.Model):
    _inherit = "account.invoice"
    
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
            if invoice_type in ('rental', 'sale', 'loss'):
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
                 
    journal_id = fields.Many2one('account.journal', string='Journal',
        required=True, readonly=True, states={'draft': [('readonly', False)]},
        default=_default_journal,
        domain="[('type', 'in', {'out_invoice': ['sale'], 'out_refund': ['sale'], 'in_refund': ['purchase'], 'in_invoice': ['purchase']}.get(type, [])), ('company_id', '=', company_id)]")
    kiosk_id = fields.Many2one('stock.location', string='Kiosk *')
    date_start = fields.Datetime(string='Start date')
    date_end = fields.Datetime(string='End date')
    invoice_type = fields.Selection([('rental', 'Rental'), ('sale', 'Sale'), ('loss', 'Loss')], string="Type invoice", default=_default_account_type)
    
    kiosk_id = fields.Many2one('stock.location', string='Kiosk *')
    date_start = fields.Date(string='Billing start date')
    date_end = fields.Date(string='Billing end date')
    
    state = fields.Selection([
            ('draft', 'Draft'),
            ('proforma2', 'Open'),
            ('open', 'Validated'),
            ('partially_paid', 'Partially paid'),
            ('paid', 'Paid'),
            ('cancel', 'Cancelled'),
        ], string='Status', index=True, readonly=True, default='draft',
        track_visibility='onchange', copy=False,
        help=" * The 'Draft' status is used when a user is encoding a new and unconfirmed Invoice.\n"
             " * The 'Pro-forma' status is used when the invoice does not have an invoice number.\n"
             " * The 'Open' status is used when user creates invoice, an invoice number is generated. It stays in the open status till the user pays the invoice.\n"
             " * The 'Paid' status is set automatically when the invoice is paid. Its related journal entries may or may not be reconciled.\n"
             " * The 'Cancelled' status is used when user cancel invoice.")
    
    def get_move_lines(self, type_move='in'):
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
                    'number_days': delta.days + 1,
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
        moves += self.get_move_lines('in')
        moves += self.get_move_lines('out')
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
            
            if not self.kiosk_id.billing_table_id:
                raise UserError(_('Error!/nNo billing table created for this kiosk'))
            table_id = self.kiosk_id.billing_table_id
            current_month = date_end.month
            table_line = BillingTableLine.search([('table_id', '=', table_id.id), ('month', '=', current_month)], limit=1)
            if not table_line:
                raise UserError(_('Error configuration!/nPlease configure billing table for this current month'))
            number_days = table_line.number_days
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
        self.price_subtotal = price_subtotal_signed = "{:.0f}".format(taxes['total_excluded'] if taxes else self.quantity * price)
        if self.invoice_id.currency_id and self.invoice_id.company_id and self.invoice_id.currency_id != self.invoice_id.company_id.currency_id:
            price_subtotal_signed = self.invoice_id.currency_id.with_context(date=self.invoice_id.date_invoice).compute(price_subtotal_signed, self.invoice_id.company_id.currency_id)
        sign = self.invoice_id.type in ['in_refund', 'out_refund'] and -1 or 1
        self.price_subtotal_signed = price_subtotal_signed * sign
    
    date = fields.Date(string='Date', default=fields.Date.context_today)
    number_days = fields.Float(string='Days', digits=dp.get_precision('Product Unit of Measure'), default=1.0)


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