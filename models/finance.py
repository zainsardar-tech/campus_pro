from odoo import models, fields, api, _

class CampusFeeType(models.Model):
    _name = 'campus.fee.type'
    _description = 'Fee Type'

    name = fields.Char(string='Fee Name', required=True, help="e.g. Monthly Tuition Fee")
    code = fields.Char(string='Code')
    is_recurring = fields.Boolean(string='Is Monthly?', default=True)

class CampusFeeStructure(models.Model):
    _name = 'campus.fee.structure'
    _description = 'Fee Structure'

    name = fields.Char(string='Structure Name', required=True)
    class_id = fields.Many2one('campus.class', string='Class', required=True)
    fee_line_ids = fields.One2many('campus.fee.line', 'structure_id', string='Fee Lines')

class CampusFeeLine(models.Model):
    _name = 'campus.fee.line'
    _description = 'Fee Structure Line'

    structure_id = fields.Many2one('campus.fee.structure', string='Structure')
    fee_type_id = fields.Many2one('campus.fee.type', string='Fee Type', required=True)
    amount = fields.Float(string='Amount', required=True)

class CampusFeeFineRule(models.Model):
    _name = 'campus.fee.fine_rule'
    _description = 'Fee Fine Rule'

    name = fields.Char(string='Rule Name', required=True)
    fine_type = fields.Selection([
        ('fixed', 'Fixed Amount'),
        ('per_day', 'Amount Per Day')
    ], string='Fine Type', default='fixed')
    amount = fields.Float(string='Fine Amount', required=True)
    grace_period = fields.Integer(string='Grace Period (Days)', default=0)
    active = fields.Boolean(default=True)

class CampusFeeChallan(models.Model):
    _name = 'campus.fee.challan'
    _description = 'Fee Challan'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Challan Number', readonly=True, copy=False, default=lambda self: _('New'))
    student_id = fields.Many2one('campus.student', string='Student', required=True, ondelete='cascade')
    session_id = fields.Many2one('campus.session', string='Session', required=True)
    month = fields.Selection([
        ('1', 'January'), ('2', 'February'), ('3', 'March'), ('4', 'April'),
        ('5', 'May'), ('6', 'June'), ('7', 'July'), ('8', 'August'),
        ('9', 'September'), ('10', 'October'), ('11', 'November'), ('12', 'December')
    ], string='Month', required=True)
    
    date_issue = fields.Date(string='Issue Date', default=fields.Date.today)
    date_due = fields.Date(string='Due Date', required=True)
    
    amount_total = fields.Float(string='Total Amount', compute='_compute_totals', store=True)
    amount_paid = fields.Float(string='Paid Amount')
    amount_residual = fields.Float(string='Residual', compute='_compute_totals', store=True)
    
    discount_amount = fields.Float(string='Discount / Scholarship', tracking=True)
    discount_approved = fields.Boolean(string='Discount Approved', default=False, tracking=True)
    discount_reason = fields.Char(string='Discount Reason', tracking=True)
    fine_amount = fields.Float(string='Late Fee Fine', compute='_compute_fine', store=True)
    
    state = fields.Selection([
        ('draft', 'Draft'),
        ('posted', 'Published'),
        ('paid', 'Paid'),
        ('partial', 'Partially Paid'),
        ('cancel', 'Cancelled')
    ], string='Status', default='draft', tracking=True)
    
    line_ids = fields.One2many('campus.fee.challan.line', 'challan_id', string='Challan Lines')
    invoice_id = fields.Many2one('account.move', string='Related Invoice', readonly=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('campus.fee.challan') or _('New')
        return super().create(vals_list)

    @api.depends('line_ids.amount', 'amount_paid', 'discount_amount', 'discount_approved', 'fine_amount')
    def _compute_totals(self):
        for rec in self:
            subtotal = sum(rec.line_ids.mapped('amount'))
            discount = rec.discount_amount if rec.discount_approved else 0.0
            total = subtotal - discount + rec.fine_amount
            rec.amount_total = total
            rec.amount_residual = total - rec.amount_paid

    @api.depends('date_due', 'state')
    def _compute_fine(self):
        for rec in self:
            if rec.state in ['paid', 'cancel'] or not rec.date_due:
                rec.fine_amount = 0.0
                continue
            
            today = fields.Date.today()
            if today > rec.date_due:
                rule = self.env['campus.fee.fine_rule'].search([('active', '=', True)], limit=1)
                if rule:
                    days_late = (today - rec.date_due).days
                    if days_late > rule.grace_period:
                        if rule.fine_type == 'fixed':
                            rec.fine_amount = rule.amount
                        else:
                            rec.fine_amount = rule.amount * days_late
                    else:
                        rec.fine_amount = 0.0
                else:
                    rec.fine_amount = 0.0
            else:
                rec.fine_amount = 0.0

    def action_post(self):
        for rec in self:
            rec.state = 'posted'
            if not rec.invoice_id:
                rec._create_invoice()

    def _create_invoice(self):
        self.ensure_one()
        # Find a suitable journal
        journal = self.env['account.journal'].search([('type', '=', 'sale')], limit=1)
        if not journal:
            return False
            
        invoice_vals = {
            'move_type': 'out_invoice',
            'partner_id': self.env.user.partner_id.id, # Placeholder: link to student's partner if possible
            'journal_id': journal.id,
            'invoice_date': self.date_issue,
            'invoice_line_ids': [],
        }
        
        # Add basic fee lines
        for line in self.line_ids:
            invoice_vals['invoice_line_ids'].append((0, 0, {
                'name': f"{line.fee_type_id.name} - {self.student_id.name}",
                'quantity': 1,
                'price_unit': line.amount,
            }))
            
        # Add Discount
        if self.discount_amount > 0 and self.discount_approved:
             invoice_vals['invoice_line_ids'].append((0, 0, {
                'name': _('Scholarship / Discount'),
                'quantity': 1,
                'price_unit': -self.discount_amount,
            }))

        # Add Fine
        if self.fine_amount > 0:
             invoice_vals['invoice_line_ids'].append((0, 0, {
                'name': _('Late Fee Fine'),
                'quantity': 1,
                'price_unit': self.fine_amount,
            }))
            
        invoice = self.env['account.move'].create(invoice_vals)
        self.invoice_id = invoice.id
        return invoice

    def action_send_whatsapp_reminder(self):
        self.ensure_one()
        if not self.student_id.guardian_phone:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _("Missing Contact"),
                    'message': _("Guardian phone number not found!"),
                    'type': 'danger',
                }
            }
        
        month_dict = dict(self._fields['month'].selection)
        data = {
            'student_id': self.student_id.id,
            'student_name': self.student_id.name,
            'month': month_dict.get(self.month),
            'amount': self.amount_residual,
            'due_date': self.date_due,
            'challan_no': self.name,
            'challan': self,
        }
        
        # Try auto-trigger/logging via service
        res = self.env['campus.whatsapp.service'].send_event_message('fee_challan', self.student_id.guardian_phone, data, manual=True)
        if res:
             # Handle response for UI feedback
             if isinstance(res, dict) and res.get('status'):
                 return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _("WhatsApp Sent"),
                        'message': _("Fee reminder has been sent successfully."),
                        'type': 'success',
                    }
                }
             elif isinstance(res, dict):
                 return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _("Send Failed"),
                        'message': res.get('msg', _("Unknown error occurred.")),
                        'type': 'danger',
                        'sticky': True,
                    }
                }

        # Fallback to manual if no template or trigger disabled
        message = self.env['campus.whatsapp.service'].get_event_message('fee_challan', data)
        if not message:
            message = _(
                "🔔 *Fee Reminder - Campus Pro*\n\n"
                "Dear Guardian,\n"
                "This is a reminder for the fee challan of *%(student)s* for the month of *%(month)s*.\n\n"
                "🔹 Challan No: %(name)s\n"
                "🔹 Amount Due: *PKR %(amount).2f*\n"
                "🔹 Due Date: %(due)s\n\n"
                "Please clear the dues before the deadline. Thank you!"
            ) % {
                'student': self.student_id.name,
                'month': data['month'],
                'name': self.name,
                'amount': self.amount_residual,
                'due': self.date_due
            }
        
        result = self.env['campus.whatsapp.service'].send_text(self.student_id.guardian_phone, message)
        
        if result.get('status'):
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _("WhatsApp Sent"),
                    'message': _("Fee reminder has been sent successfully."),
                    'type': 'success',
                }
            }
        else:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _("Send Failed"),
                    'message': result.get('msg', _("Unknown error occurred.")),
                    'type': 'danger',
                    'sticky': True,
                }
            }

class CampusFeeChallanLine(models.Model):
    _name = 'campus.fee.challan.line'
    _description = 'Challan Line'

    challan_id = fields.Many2one('campus.fee.challan', string='Challan')
    fee_type_id = fields.Many2one('campus.fee.type', string='Fee Type', required=True)
    amount = fields.Float(string='Amount', required=True)
