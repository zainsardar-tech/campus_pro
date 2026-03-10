from odoo import models, fields, api, _

class CampusExam(models.Model):
    _name = 'campus.exam'
    _description = 'Examination'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Exam Name', required=True, help="e.g. Mid Term 2024")
    session_id = fields.Many2one('campus.session', string='Academic Session', required=True)
    exam_type = fields.Selection([
        ('monthly', 'Monthly Test'),
        ('mid', 'Mid Term'),
        ('final', 'Final Exam'),
        ('other', 'Other')
    ], string='Exam Type', required=True)
    
    date_start = fields.Date(string='Start Date')
    date_end = fields.Date(string='End Date')
    
    state = fields.Selection([
        ('draft', 'Draft'),
        ('scheduled', 'Scheduled'),
        ('ongoing', 'Ongoing'),
        ('completed', 'Completed'),
        ('published', 'Result Published')
    ], string='Status', default='draft', tracking=True)

    def action_schedule(self):
        for rec in self:
            rec.state = 'scheduled'

    def action_publish(self):
        for rec in self:
            rec.state = 'published'
            # Logic for WhatsApp notification can be added here

class CampusExamResult(models.Model):
    _name = 'campus.exam.result'
    _description = 'Student Exam Result'

    exam_id = fields.Many2one('campus.exam', string='Exam', required=True)
    student_id = fields.Many2one('campus.student', string='Student', required=True, ondelete='cascade')
    subject_id = fields.Many2one('campus.subject', string='Subject', required=True)
    
    max_marks = fields.Float(string='Total Marks', default=100.0)
    obtained_marks = fields.Float(string='Obtained Marks')
    percentage = fields.Float(string='Percentage', compute='_compute_percentage', store=True)
    grade = fields.Char(string='Grade', compute='_compute_percentage', store=True)

    @api.depends('obtained_marks', 'max_marks')
    def _compute_percentage(self):
        for rec in self:
            if rec.max_marks > 0:
                rec.percentage = (rec.obtained_marks / rec.max_marks) * 100
                # Basic grading logic
                if rec.percentage >= 90: rec.grade = 'A+'
                elif rec.percentage >= 80: rec.grade = 'A'
                elif rec.percentage >= 70: rec.grade = 'B'
                elif rec.percentage >= 60: rec.grade = 'C'
                elif rec.percentage >= 50: rec.grade = 'D'
                else: rec.grade = 'F'
            else:
                rec.percentage = 0
                rec.grade = '-'
