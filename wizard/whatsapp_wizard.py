from odoo import models, fields, api, _

class CampusWhatsappWizard(models.TransientModel):
    _name = 'campus.whatsapp.wizard'
    _description = 'Custom WhatsApp Message Wizard'

    student_id = fields.Many2one('campus.student', string='Student', required=True)
    mobile = fields.Char(string='Mobile Number', required=True)
    message = fields.Text(string='Message', required=True)
    
    def action_send_message(self):
        self.ensure_one()
        result = self.env['campus.whatsapp.service'].send_text(self.mobile, self.message)
        if result.get('status'):
            if self.student_id:
                self.student_id.message_post(body=_("WhatsApp Sent: %s") % self.message)
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _("Message Sent"),
                    'message': _("Custom WhatsApp message sent successfully."),
                    'type': 'success',
                }
            }
        else:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _("Send Failed"),
                    'message': result.get('msg', _("Failed to send custom WhatsApp message.")),
                    'type': 'danger',
                    'sticky': True,
                }
            }
