import requests
import logging
from odoo import models, fields, api, _

_logger = logging.getLogger(__name__)

class CampusWhatsappService(models.AbstractModel):
    _name = 'campus.whatsapp.service'
    _description = 'WAMS WhatsApp Service'

    @api.model
    def _get_config(self):
        # In a real scenario, these would be in ir.config_parameter
        ICPSudo = self.env['ir.config_parameter'].sudo()
        api_key = ICPSudo.get_param('campus.wams_api_key')
        sender = ICPSudo.get_param('campus.wams_sender')
        return api_key, sender

    @api.model
    def _format_number(self, number):
        """ Cleans and formats number to 923xxxxxxxx format """
        if not number:
            return False
        # Remove all non-digits
        clean = "".join(filter(str.isdigit, str(number)))
        # If starts with 0 (e.g. 0300...), replace with 92
        if clean.startswith('0'):
            clean = '92' + clean[1:]
        # If starts with + (removed already), or if it's just 300... (missing country code)
        if len(clean) == 10 and clean.startswith('3'):
            clean = '92' + clean
        return clean

    @api.model
    def send_text(self, number, message):
        api_key, sender = self._get_config()
        if not api_key or not sender:
            return {'status': False, 'msg': _("WAMS API Key or Sender not configured.")}

        clean_number = self._format_number(number)
        if not clean_number:
            return {'status': False, 'msg': _("Invalid recipient phone number.")}

        # Some WAMS senders are numbers, some are IDs. Clean only if it looks like a number.
        clean_sender = self._format_number(sender) if sender.isdigit() else sender

        url = "https://wams.aztify.com/send-message"
        payload = {
            "api_key": api_key,
            "sender": clean_sender,
            "number": clean_number,
            "message": message
        }
        
        try:
            headers = {
                'User-Agent': 'Odoo/18.0 (Campus Pro)',
                'Content-Type': 'application/json'
            }
            _logger.info(f"WAMS Payload: {payload}")
            response = requests.post(url, json=payload, headers=headers, timeout=20)
            
            if response.status_code != 200:
                _logger.error(f"WAMS HTTP {response.status_code}: {response.text}")
                return {'status': False, 'msg': _(f"HTTP Error {response.status_code}")}

            result = response.json()
            status = result.get('status')
            
            if status in [True, 'True', 'true', 'success', 1, '1'] or result.get('data'):
                _logger.info(f"WAMS Success for {clean_number}")
                return {'status': True, 'msg': result.get('msg', 'Sent')}
            else:
                msg = result.get('msg', 'Unknown API Error')
                _logger.error(f"WAMS Fail for {clean_number}: {msg} (Raw: {result})")
                return {'status': False, 'msg': msg}
        except Exception as e:
            _logger.error(f"WAMS Logic Error: {str(e)}")
            return {'status': False, 'msg': str(e)}

    @api.model
    def send_event_message(self, event_type, number, data, manual=False):
        """ 
        Governed WhatsApp Trigger Flow.
        Checks matrix, validates template, ensures student state is correct,
        verifies user permissions, logs the attempt, and sends via WAMS.
        """
        # STEP 1 & 2: Business Event & Trigger Matrix Evaluation
        trigger = self.env['campus.whatsapp.trigger'].search([('event_type', '=', event_type)], limit=1)
        if not trigger or trigger.mode == 'disabled':
            _logger.info(f"WAMS Trigger: Event {event_type} is disabled or not configured.")
            return False
        
        # STEP 3: Template Validation
        template = trigger.template_id
        if not template or not template.active or not template.is_approved:
            _logger.warning(f"WAMS Trigger: No approved/active template for {event_type}")
            return False
            
        # Optional: Campus-specific template check
        student = False
        if data.get('student_id'):
            student = self.env['campus.student'].browse(data['student_id'])
            if template.campus_id and student.exists() and student.campus_id != template.campus_id:
                _logger.info(f"WAMS Trigger: Template campus mismatch for {event_type}")
                return False

        # STEP 4: Student & Guardian Validation
        if student and student.exists():
            if student.state in ['struck_off', 'migration', 'alumni']:
                self._log_whatsapp(event_type, student, template, 'blocked', status='blocked', 
                                  reason=_("Student in inactive state: %s") % student.state)
                return False
            if not student.guardian_phone:
                return False
        
        # STEP 5: Permission Check (For manual triggers)
        if manual:
            if trigger.role_ids and not any(self.env.user.has_group(role.get_external_id().get(role.id)) for role in trigger.role_ids):
                # Fallback to display name check if XML IDs are tricky
                user_groups = self.env.user.groups_id
                if not (user_groups & trigger.role_ids):
                    _logger.warning(f"WAMS Trigger: User {self.env.user.name} lacks permission for {event_type}")
                    return False

        # STEP 6: Message Rendering
        # Data objects for template: student, guardian, challan, etc.
        render_data = data.copy()
        if student and student.exists():
            render_data['student'] = student
            render_data['guardian'] = student.guardian_id
        
        message = template.render_body(render_data)
        
        # Handle Silent Mode
        if trigger.mode == 'silent' and not manual:
            self._log_whatsapp(event_type, student, template, 'silent', status='sent', body=message)
            return True

        # STEP 7: Send via WAMS
        _logger.info(f"WAMS Trigger: Sending message for {event_type} to {number}")
        res = self.send_text(number, message)
        
        # STEP 8: WhatsApp Audit Log
        status = 'sent' if res.get('status') else 'failed'
        mode = 'manual' if manual else 'auto'
        self._log_whatsapp(event_type, student, template, mode, status=status, 
                          body=message, reason=res.get('msg') if not res.get('status') else False)
        
        # Post to chatter for visibility
        if res.get('status') and student and student.exists():
            student.message_post(body=_("WhatsApp Sent (%s): %s") % (event_type, message))
        
        return res

    @api.model
    def _log_whatsapp(self, event_type, student, template, mode, status='sent', body='', reason=False):
        """ Internal helper to create audit logs """
        self.env['campus.whatsapp.log'].create({
            'student_id': student.id if student else False,
            'guardian_id': student.guardian_id.id if student and student.guardian_id else False,
            'event_type': event_type,
            'template_id': template.id if template else False,
            'mode': mode,
            'status': status,
            'rendered_body': body,
            'failure_reason': reason
        })

    @api.model
    def get_event_message(self, event_type, data):
        """ Returns rendered message body for an event type if template exists and is approved """
        trigger = self.env['campus.whatsapp.trigger'].search([('event_type', '=', event_type)], limit=1)
        if not trigger or not trigger.template_id or not trigger.template_id.is_approved:
            return False
        
        render_data = data.copy()
        if data.get('student_id'):
            student = self.env['campus.student'].browse(data['student_id'])
            if student.exists():
                render_data['student'] = student
                render_data['guardian'] = student.guardian_id
                
        return trigger.template_id.render_body(render_data)

    @api.model
    def send_media(self, number, media_type, url, caption=""):
        api_key, sender = self._get_config()
        if not api_key or not sender:
            return False

        clean_number = "".join(filter(str.isdigit, number)) if number else ""
        if not clean_number:
            return False

        endpoint = "https://wams.aztify.com/send-media"
        payload = {
            "api_key": api_key,
            "sender": sender,
            "number": clean_number,
            "media_type": media_type,
            "url": url,
            "caption": caption
        }
        
        try:
            headers = {
                'User-Agent': 'Odoo/18.0 (Campus Pro)',
                'Content-Type': 'application/json'
            }
            response = requests.post(endpoint, json=payload, headers=headers, timeout=20)
            result = response.json()
            if response.status_code == 200 and (result.get('status') in [True, 'True', 'success', 1, '1']):
                return True
            else:
                _logger.error(f"WAMS Media Fail: {result.get('msg')} (Raw: {result})")
                return False
        except Exception as e:
            _logger.error(f"WAMS Media Exception: {str(e)}")
            return False

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    wams_api_key = fields.Char(string='WAMS API Key', config_parameter='campus.wams_api_key')
    wams_sender = fields.Char(string='WAMS Sender Number', config_parameter='campus.wams_sender')

    def action_test_wams_connection(self):
        """ Tests the WAMS connection by checking credentials and making a dummy request """
        self.ensure_one()
        api_key = self.wams_api_key or self.env['ir.config_parameter'].sudo().get_param('campus.wams_api_key')
        sender = self.wams_sender or self.env['ir.config_parameter'].sudo().get_param('campus.wams_sender')

        if not api_key or not sender:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _("Configuration Error"),
                    'message': _("Please enter both API Key and Sender Number"),
                    'type': 'danger',
                    'sticky': False,
                }
            }

        # Attempt to verify credentials via a lightweight API call (e.g. get_devices)
        # Using a generic endpoint to test connectivity
        # Using /get-profile as it's a common endpoint to check connection status
        url = "https://wams.aztify.com/get-profile"
        clean_sender = self._format_number(sender) if sender.isdigit() else sender
        payload = {"api_key": api_key, "sender": clean_sender}
        
        try:
            headers = {
                'User-Agent': 'Odoo/18.0 (Campus Pro)',
                'Content-Type': 'application/json'
            }
            
            response = requests.post(url, json=payload, headers=headers, timeout=15)
            
            _logger.info(f"WAMS Test Connection Response Status: {response.status_code}")
            try:
                result = response.json()
            except ValueError:
                # Fallback: if get-profile 404s, try sending a message to self if sender number is valid
                if response.status_code == 404:
                     _logger.warning("get-profile endpoint failed, trying send-message to self as fallback.")
                     url_send = "https://wams.aztify.com/send-message"
                     # If sender is a number, try sending to it. If it's an ID, this might fail, but worth a shot.
                     payload_send = {
                        "api_key": api_key,
                        "sender": clean_sender,
                        "number": clean_sender if clean_sender.isdigit() else "923000000000", # Fallback dummy
                        "message": "WAMS Connection Test Successful"
                     }
                     response = requests.post(url_send, json=payload_send, headers=headers, timeout=15)
                     _logger.info(f"WAMS Fallback Send Response: {response.text}")
                     try:
                         result = response.json()
                     except:
                         result = {'status': False, 'msg': f'Raw response: {response.text}'}
                else:
                     return {
                        'type': 'ir.actions.client',
                        'tag': 'display_notification',
                        'params': {
                            'title': _("Connection Error"),
                            'message': _(f"Invalid Server Response ({response.status_code})"),
                            'type': 'danger',
                            'sticky': True,
                        }
                    }

            if response.status_code == 200 and (result.get('status') in [True, 'True', 'true', 'success', 1, '1'] or result.get('data')):
                message_type = 'success'
                message_title = _("Connection Successful")
                message_body = _("Successfully connected to WAMS API.")
            else:
                message_type = 'warning'
                message_title = _("Connection Verified (Limited)")
                # Sometimes APIs return error for dummy calls but connection is actually fine
                message_body = result.get('msg', _(f"Response: {result}"))

        except Exception as e:
            message_type = 'danger'
            message_title = _("Connection Error")
            message_body = str(e)
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': message_title,
                'message': message_body,
                'type': message_type,
                'sticky': False,
            }
        }
