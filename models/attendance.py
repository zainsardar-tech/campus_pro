from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class CampusAttendance(models.Model):
    _name = 'campus.attendance'
    _description = 'Attendance Record'
    _order = 'date desc'

    type = fields.Selection([
        ('student', 'Student'),
    ], string='Attendance Type', required=True, default='student')
    
    student_id = fields.Many2one('campus.student', string='Student', required=True, ondelete='cascade')
    
    date = fields.Date(string='Date', required=True, default=fields.Date.context_today)
    check_in = fields.Datetime(string='Check In', default=fields.Datetime.now)
    
    state = fields.Selection([
        ('present', 'Present'),
        ('absent', 'Absent'),
        ('late', 'Late'),
        ('leave', 'On Leave')
    ], string='Status', default='present', required=True)
    
    remarks = fields.Char(string='Remarks')
    is_locked = fields.Boolean(string='Locked', default=False, tracking=True)

    def action_lock(self):
        for rec in self:
            rec.is_locked = True
            if rec.state == 'absent':
                rec._notify_absence()

    def action_unlock(self):
        for rec in self:
            rec.is_locked = False

    def write(self, vals):
        for rec in self:
            if rec.is_locked and not self.env.su:
                raise ValidationError(_("Attendance record for %s on %s is locked.") % (rec.student_id.name, rec.date))
        return super().write(vals)

    def unlink(self):
        for rec in self:
            if rec.is_locked:
                raise ValidationError(_("Locked attendance records cannot be deleted."))
        return super().unlink()

    def _notify_absence(self):
        self.ensure_one()
        if not self.student_id.guardian_phone:
            return False
            
        data = {
            'student_id': self.student_id.id,
            'student_name': self.student_id.name,
            'date': self.date,
        }
        return self.env['campus.whatsapp.service'].send_event_message('absence', self.student_id.guardian_phone, data)


