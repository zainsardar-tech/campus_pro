from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import logging
import qrcode

_logger = logging.getLogger(__name__)
import base64
from io import BytesIO

class CampusGuardian(models.Model):
    _name = 'campus.guardian'
    _description = 'Student Guardian'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Name', required=True, tracking=True)
    relation = fields.Selection([
        ('father', 'Father'),
        ('mother', 'Mother'),
        ('brother', 'Brother'),
        ('sister', 'Sister'),
        ('other', 'Other')
    ], string='Relation', required=True)
    cnic = fields.Char(string='CNIC', help="Pakistani CNIC Format: 00000-0000000-0")
    phone = fields.Char(string='Phone / WhatsApp', required=True, tracking=True)
    whatsapp_number = fields.Char(string='WhatsApp Formatted', compute='_compute_whatsapp_number', store=True)
    email = fields.Char(string='Email')
    address = fields.Text(string='Address')
    occupation = fields.Char(string='Occupation')
    student_ids = fields.One2many('campus.student', 'guardian_id', string='Students')

    @api.depends('phone')
    def _compute_whatsapp_number(self):
        for rec in self:
            if rec.phone:
                # Basic normalization for WAMS
                num = ''.join(filter(str.isdigit, rec.phone))
                if num.startswith('0'):
                    num = '92' + num[1:]
                elif not num.startswith('92'):
                    num = '92' + num
                rec.whatsapp_number = num
            else:
                rec.whatsapp_number = False

class CampusStudent(models.Model):
    _name = 'campus.student'
    _description = 'Student Profile'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Student Name', required=True, tracking=True)
    registration_no = fields.Char(string='Registration No', readonly=True, copy=False, default=lambda self: _('New'))
    gr_no = fields.Char(string='G.R Number', required=True, tracking=True)
    
    # Personal Info
    dob = fields.Date(string='Date of Birth')
    gender = fields.Selection([
        ('male', 'Male'),
        ('female', 'Female'),
        ('other', 'Other')
    ], string='Gender')
    b_form = fields.Char(string='B-Form / CNIC')
    blood_group = fields.Selection([
        ('a+', 'A+'), ('a-', 'A-'), ('b+', 'B+'), ('b-', 'B-'),
        ('ab+', 'AB+'), ('ab-', 'AB-'), ('o+', 'O+'), ('o-', 'O-')
    ], string='Blood Group')
    
    # Contact Info
    address = fields.Text(string='Address')
    image = fields.Binary(string='Student Image')
    
    # Guardian Info
    guardian_id = fields.Many2one('campus.guardian', string='Guardian', required=True, tracking=True)
    guardian_phone = fields.Char(related='guardian_id.phone', string='Guardian Phone', readonly=True)
    
    # Academic Info
    campus_id = fields.Many2one('campus.campus', string='Campus', tracking=True)
    class_id = fields.Many2one('campus.class', string='Class', tracking=True)
    section_id = fields.Many2one('campus.section', string='Section', tracking=True)
    session_id = fields.Many2one('campus.session', string='Academic Session', default=lambda self: self.env['campus.session'].search([('active', '=', True)], limit=1))
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    
    state = fields.Selection([
        ('draft', 'Inquiry'),
        ('reserved', 'Reserved'),
        ('admission', 'Admission'),
        ('enrolled', 'Enrolled'),
        ('on_hold', 'On Hold (Fee Issue)'),
        ('struck_off', 'Struck Off'),
        ('migration', 'Migration Out'),
        ('freeze', 'Freeze (Fee Stopped)'),
        ('passed', 'Passed'),
        ('alumni', 'Alumni')
    ], string='Status', default='draft', tracking=True)
    
    is_fee_frozen = fields.Boolean(string='Fee Stopped', default=False, tracking=True)
    
    enrollment_ids = fields.One2many('campus.enrollment', 'student_id', string='Enrollment History')
    status_log_ids = fields.One2many('campus.student.status.log', 'student_id', string='Status History')
    
    # Intelligence Fields
    attendance_percentage = fields.Float(string='Attendance %', compute='_compute_academic_intelligence')
    exam_eligibility = fields.Boolean(string='Exam Eligible', compute='_compute_academic_intelligence')
    dropout_risk = fields.Selection([
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High')
    ], string='Dropout Risk', compute='_compute_academic_intelligence', store=True)

    def _compute_academic_intelligence(self):
        for rec in self:
            records = self.env['campus.attendance'].search([('student_id', '=', rec.id)])
            total = len(records)
            present = len(records.filtered(lambda a: a.state in ['present', 'late']))
            
            percentage = (present / total * 100) if total > 0 else 0.0
            rec.attendance_percentage = percentage
            rec.exam_eligibility = percentage >= 75.0
            
            # Dropout risk logic: High if 3 consecutive absences or < 50% attendance
            if total > 0 and percentage < 50.0:
                 rec.dropout_risk = 'high'
            elif total > 0 and percentage < 70.0:
                 rec.dropout_risk = 'medium'
            else:
                 rec.dropout_risk = 'low'
    
    # QR Code
    qr_code = fields.Binary(string='QR Code', compute='_generate_qr_code', store=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('registration_no', _('New')) == _('New'):
                vals['registration_no'] = self.env['ir.sequence'].next_by_code('campus.student') or _('New')
        return super().create(vals_list)

    @api.depends('registration_no')
    def _generate_qr_code(self):
        for rec in self:
            if rec.registration_no:
                qr = qrcode.QRCode(version=1, box_size=10, border=5)
                qr.add_data(rec.registration_no)
                qr.make(fit=True)
                img = qr.make_image(fill='black', back_color='white')
                temp = BytesIO()
                img.save(temp, format="PNG")
                qr_image = base64.b64encode(temp.getvalue())
                rec.qr_code = qr_image

    @api.model
    def get_dashboard_stats(self):
        today = fields.Date.today()
        
        # Student count
        students_count = self.search_count([('state', '=', 'enrolled')])
        
        # Recent students
        recent_students = self.search_read(
            [('state', 'in', ['draft', 'admission', 'enrolled'])], 
            ['name', 'class_id', 'state', 'create_date'], 
            limit=5, order='create_date desc'
        )
        
        # Fee collection
        challans = self.env['campus.fee.challan'].search([('state', 'in', ['posted', 'paid', 'partial'])])
        fees_collected = sum(challans.mapped('amount_paid'))
        fees_total = sum(challans.mapped('amount_total'))
        
        # Defaulters
        defaulters = self.env['campus.fee.challan'].search_count([
            ('state', '=', 'posted'), 
            ('amount_residual', '>', 0),
            ('date_due', '<', today)
        ])
        
        # Real attendance percentage for today
        attendance_records = self.env['campus.attendance'].search([('date', '=', today)])
        total_attendance = len(attendance_records)
        present_attendance = len(attendance_records.filtered(lambda a: a.state in ['present', 'late']))
        attendance_today = (present_attendance / total_attendance * 100) if total_attendance > 0 else 0.0
        
        # Intelligence Stats
        enrolled_students = self.search([('state', '=', 'enrolled')])
        ineligible_count = len(enrolled_students.filtered(lambda s: not s.exam_eligibility))
        high_risk_count = self.search_count([('state', '=', 'enrolled'), ('dropout_risk', 'in', ['medium', 'high'])])
        
        # Enrollment Trends (Last 6 months)
        trends_labels = []
        trends_data = []
        from dateutil.relativedelta import relativedelta
        for i in range(5, -1, -1):
            date_start = today - relativedelta(months=i)
            month_label = date_start.strftime('%b %Y')
            month_start = date_start.replace(day=1)
            next_month = month_start + relativedelta(months=1)
            
            count = self.search_count([
                ('create_date', '>=', month_start),
                ('create_date', '<', next_month)
            ])
            trends_labels.append(month_label)
            trends_data.append(count)

        # Class-wise distribution
        classes = self.env['campus.class'].search([])
        class_labels = []
        class_data = []
        for cls in classes:
            count = self.search_count([('class_id', '=', cls.id), ('state', '=', 'enrolled')])
            if count > 0:
                class_labels.append(cls.name)
                class_data.append(count)

        # Enrollment Trends (Last 7 Days - Bar)
        daily_labels = []
        daily_data = []
        for i in range(6, -1, -1):
            date_target = today - relativedelta(days=i)
            daily_labels.append(date_target.strftime('%a'))
            count = self.search_count([
                ('create_date', '>=', date_target),
                ('create_date', '<', date_target + relativedelta(days=1))
            ])
            daily_data.append(count)

        # Gender distribution
        gender_labels = ['Male', 'Female', 'Other']
        gender_data = [
            self.search_count([('gender', '=', 'male'), ('state', '=', 'enrolled')]),
            self.search_count([('gender', '=', 'female'), ('state', '=', 'enrolled')]),
            self.search_count([('gender', '=', 'other'), ('state', '=', 'enrolled')])
        ]

        # WhatsApp Config Status
        ICPSudo = self.env['ir.config_parameter'].sudo()
        wams_connected = bool(ICPSudo.get_param('campus.wams_api_key') and ICPSudo.get_param('campus.wams_sender'))

        return {
            'students': students_count,
            'recent_students': recent_students,
            'fees_collected': fees_collected,
            'fees_total': fees_total,
            'defaulters': defaulters,
            'attendance_today': attendance_today,
            'wams_connected': wams_connected,
            'high_risk_count': high_risk_count,
            'ineligible_count': ineligible_count,
            'trends': {
                'labels': trends_labels,
                'data': trends_data,
            },
            'daily_trends': {
                'labels': daily_labels,
                'data': daily_data,
            },
            'class_dist': {
                'labels': class_labels,
                'data': class_data,
            },
            'gender_dist': {
                'labels': gender_labels,
                'data': gender_data,
            },
            'fee_stats': {
                'paid': fees_collected,
                'unpaid': fees_total - fees_collected,
            }
        }

    def action_confirm_admission(self):
        for rec in self:
            rec.state = 'admission'

    def action_enroll(self):
        for rec in self:
            if not rec.class_id or not rec.session_id:
                raise ValidationError(_("Please specify Class and Session before enrollment."))
            rec.state = 'enrolled'
            # Create enrollment record if it doesn't exist
            existing = self.env['campus.enrollment'].search([
                ('student_id', '=', rec.id),
                ('session_id', '=', rec.session_id.id),
                ('class_id', '=', rec.class_id.id)
            ])
            if not existing:
                self.env['campus.enrollment'].create({
                    'student_id': rec.id,
                    'session_id': rec.session_id.id,
                    'class_id': rec.class_id.id,
                    'section_id': rec.section_id.id if rec.section_id else False
                })

    def action_reserve(self):
        for rec in self:
            rec.state = 'reserved'

    def action_on_hold(self):
        for rec in self:
            rec.state = 'on_hold'

    def action_struck_off(self):
        for rec in self:
            rec.state = 'struck_off'

    def action_reset_to_draft(self):
        for rec in self:
            rec.state = 'draft'

    def action_migrate(self):
        for rec in self:
            rec.state = 'migration'

    def action_passed(self):
        for rec in self:
            rec.state = 'passed'

    def action_freeze(self):
        for rec in self:
            rec.state = 'freeze'
            rec.is_fee_frozen = True

    def action_alumni(self):
        for rec in self:
            rec.state = 'alumni'

    def write(self, vals):
        if 'state' in vals:
            for rec in self:
                if rec.state != vals['state']:
                    self.env['campus.student.status.log'].create({
                        'student_id': rec.id,
                        'previous_state': dict(self._fields['state'].selection).get(rec.state or 'draft'),
                        'new_state': dict(self._fields['state'].selection).get(vals['state']),
                    })
                    if vals['state'] == 'admission':
                        rec.action_send_admission_msg()
        return super(CampusStudent, self).write(vals)

    def action_send_admission_msg(self):
        self.ensure_one()
        if not self.guardian_phone:
            return False
            
        data = {
            'student_id': self.id,
            'student_name': self.name,
            'class_name': self.class_id.name,
        }
        # Try auto-trigger first
        res = self.env['campus.whatsapp.service'].send_event_message('admission', self.guardian_phone, data)
        if res:
            return res.get('status') if isinstance(res, dict) else res

        # Manual/Fallback
        message = self.env['campus.whatsapp.service'].get_event_message('admission', data)
        if not message:
             message = _(
                "🎓 *Welcome to Campus Pro!*\n\n"
                "Congratulations! Your child *%(student)s* has been successfully enrolled in *%(class)s*.\n\n"
                "Best Regards,\n"
                "School Management"
            ) % {
                'student': self.name,
                'class': self.class_id.name
            }
        
        res = self.env['campus.whatsapp.service'].send_text(self.guardian_phone, message)
        return res.get('status') if isinstance(res, dict) else res

    def action_open_whatsapp_wizard(self):
        self.ensure_one()
        return {
            'name': _('Send WhatsApp Message'),
            'type': 'ir.actions.act_window',
            'res_model': 'campus.whatsapp.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_student_id': self.id,
                'default_mobile': self.guardian_phone,
            }
        }

class CampusStudentStatusLog(models.Model):
    _name = 'campus.student.status.log'
    _description = 'Student Status History'
    _order = 'create_date desc'

    student_id = fields.Many2one('campus.student', string='Student', ondelete='cascade')
    previous_state = fields.Char(string='From')
    new_state = fields.Char(string='To')
    reason = fields.Text(string='Reason')
    user_id = fields.Many2one('res.users', string='Changed By', default=lambda self: self.env.user)

class CampusEnrollment(models.Model):
    _name = 'campus.enrollment'
    _description = 'Student Enrollment Record'

    student_id = fields.Many2one('campus.student', string='Student', required=True, ondelete='cascade')
    session_id = fields.Many2one('campus.session', string='Session', required=True)
    class_id = fields.Many2one('campus.class', string='Class', required=True)
    section_id = fields.Many2one('campus.section', string='Section', required=True)
    roll_no = fields.Char(string='Roll Number')
    active = fields.Boolean(default=True)
