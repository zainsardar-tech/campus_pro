from odoo import models, fields, api, _

class CampusWhatsappLog(models.Model):
    _name = 'campus.whatsapp.log'
    _description = 'WhatsApp Audit Log'
    _order = 'timestamp desc'
    _rec_name = 'event_type'

    student_id = fields.Many2one('campus.student', string='Student', ondelete='set null')
    guardian_id = fields.Many2one('campus.guardian', string='Guardian', ondelete='set null')
    event_type = fields.Selection([
        ('admission', 'Admission Confirmation'),
        ('fee_challan', 'Fee Challan Created'),
        ('absence', 'Student Absence'),
        ('exam_result', 'Exam Result Published'),
        ('manual', 'Manual Message')
    ], string='Event', required=True)
    
    template_id = fields.Many2one('campus.whatsapp.template', string='Template Used')
    mode = fields.Selection([
        ('auto', 'Auto Send'),
        ('manual', 'Manual Send'),
        ('silent', 'Silent Log'),
        ('blocked', 'Blocked')
    ], string='Mode')
    
    user_id = fields.Many2one('res.users', string='Sent By', default=lambda self: self.env.user)
    status = fields.Selection([
        ('sent', 'Sent'),
        ('failed', 'Failed'),
        ('blocked', 'Blocked')
    ], string='Status', required=True)
    
    rendered_body = fields.Text(string='Message Content')
    timestamp = fields.Datetime(string='Date & Time', default=fields.Datetime.now)
    failure_reason = fields.Char(string='Failure Reason')
