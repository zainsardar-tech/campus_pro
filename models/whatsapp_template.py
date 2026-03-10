from odoo import models, fields, api, _
import re

class CampusWhatsappTemplate(models.Model):
    _name = 'campus.whatsapp.template'
    _description = 'WhatsApp Message Template'

    name = fields.Char(string='Name', required=True)
    body = fields.Text(string='Message Body', required=True, 
                      help="Use {{variable}} for placeholders. e.g. {{student_name}}")
    event_type = fields.Selection([
        ('admission', 'On Admission'),
        ('fee_challan', 'On Fee Challan'),
        ('absence', 'On Absence'),
        ('exam_result', 'On Exam Result'),
        ('custom', 'Custom Message')
    ], string='Event Type', required=True)
    lang = fields.Selection([
        ('en', 'English'),
        ('roman_urdu', 'Roman Urdu')
    ], string='Language', default='en')
    campus_id = fields.Many2one('campus.campus', string='Campus', help="If set, this template only applies to this campus.")
    is_approved = fields.Boolean(string='Approved?', default=False, tracking=True)
    active = fields.Boolean(default=True)

    def render_body(self, data):
        """ 
        Safe render placeholders in the body with provided data.
        Data keys can be simple values or Odoo recordsets.
        """
        self.ensure_one()
        rendered_body = self.body
        
        # Regex to find all {{object.field}} or {{field}}
        placeholders = re.findall(r'\{\{(.*?)\}\}', rendered_body)
        
        for p in placeholders:
            val = ''
            p_strip = p.strip()
            
            if '.' in p_strip:
                # Handle objects: student.name, challan.amount_residual
                obj_name, field_name = p_strip.split('.', 1)
                obj = data.get(obj_name)
                if obj and hasattr(obj, field_name):
                    val = getattr(obj, field_name)
                    # If it's a many2one, take the name
                    if hasattr(val, 'display_name'):
                        val = val.display_name
            else:
                # Handle simple keys
                val = data.get(p_strip, '')
            
            rendered_body = rendered_body.replace('{{%s}}' % p, str(val if val is not False else ''))
            
        return rendered_body

class CampusWhatsappTriggerMatrix(models.Model):
    _name = 'campus.whatsapp.trigger'
    _description = 'WhatsApp Trigger Matrix'
    _rec_name = 'event_type'

    event_type = fields.Selection([
        ('admission', 'Admission Confirmation'),
        ('fee_challan', 'Fee Challan Created'),
        ('absence', 'Student Absence'),
        ('exam_result', 'Exam Result Published')
    ], string='Event', required=True)
    
    mode = fields.Selection([
        ('auto', 'Auto Send'),
        ('manual', 'Manual (Show Button)'),
        ('disabled', 'Disabled'),
        ('silent', 'Silent (Log only)')
    ], string='Mode', default='manual', required=True)
    
    template_id = fields.Many2one('campus.whatsapp.template', string='Default Template', 
                                 domain="[('event_type', '=', event_type), ('is_approved', '=', True)]")
    
    role_ids = fields.Many2many('res.groups', string='Allowed Groups', 
                               help="Only users in these groups can trigger this manually.")
    
    _sql_constraints = [
        ('unique_event', 'unique(event_type)', 'Trigger settings already exist for this event!')
    ]
