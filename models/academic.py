from odoo import models, fields, api

class CampusSession(models.Model):
    _name = 'campus.session'
    _description = 'Academic Session'
    _order = 'date_start desc'

    name = fields.Char(string='Session Name', required=True, help="e.g. 2024-25")
    date_start = fields.Date(string='Start Date', required=True)
    date_end = fields.Date(string='End Date', required=True)
    active = fields.Boolean(default=True)

class CampusCampus(models.Model):
    _name = 'campus.campus'
    _description = 'Institute Campus'

    name = fields.Char(string='Campus Name', required=True)
    code = fields.Char(string='Campus Code')
    address = fields.Text(string='Address')
    phone = fields.Char(string='Phone')
    email = fields.Char(string='Email')
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)

class CampusClass(models.Model):
    _name = 'campus.class'
    _description = 'Class/Level'

    name = fields.Char(string='Class Name', required=True)
    code = fields.Char(string='Class Code')
    sequence = fields.Integer(default=10)

class CampusSection(models.Model):
    _name = 'campus.section'
    _description = 'Class Section'

    name = fields.Char(string='Section Name', required=True)
    class_id = fields.Many2one('campus.class', string='Class', required=True)
    campus_id = fields.Many2one('campus.campus', string='Campus', required=True)
    teacher_id = fields.Many2one('hr.employee', string='Class Teacher')

class CampusSubject(models.Model):
    _name = 'campus.subject'
    _description = 'Subject'

    name = fields.Char(string='Subject Name', required=True)
    code = fields.Char(string='Subject Code')
    type = fields.Selection([
        ('theory', 'Theory'),
        ('practical', 'Practical'),
        ('both', 'Both')
    ], string='Type', default='theory')
    class_ids = fields.Many2many('campus.class', string='Classes')
