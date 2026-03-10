from odoo import models, fields, api

class ResCompany(models.Model):
    _inherit = 'res.company'

    campus_id_card_header_text = fields.Char(string="Header Text", default="Campus Pro Institute")
    campus_id_card_sub_header_text = fields.Char(string="Sub Header Text", default="Excellence in Education")
    campus_id_card_primary_color = fields.Char(string="Primary Color", default="#1e3a8a", help="Hex color code (e.g. #1e3a8a)")
    campus_id_card_secondary_color = fields.Char(string="Secondary Color", default="#3b82f6", help="Hex color code (e.g. #3b82f6)")
    campus_id_card_show_qr = fields.Boolean(string="Show QR Code", default=True)
    campus_id_card_show_address = fields.Boolean(string="Show Address", default=True)
    campus_id_card_show_bform = fields.Boolean(string="Show B-Form/CNIC", default=True)
    campus_id_card_show_emergency = fields.Boolean(string="Show Emergency Contact", default=True)

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    campus_id_card_header_text = fields.Char(related='company_id.campus_id_card_header_text', readonly=False)
    campus_id_card_sub_header_text = fields.Char(related='company_id.campus_id_card_sub_header_text', readonly=False)
    campus_id_card_primary_color = fields.Char(related='company_id.campus_id_card_primary_color', readonly=False)
    campus_id_card_secondary_color = fields.Char(related='company_id.campus_id_card_secondary_color', readonly=False)
    campus_id_card_show_qr = fields.Boolean(related='company_id.campus_id_card_show_qr', readonly=False)
    campus_id_card_show_address = fields.Boolean(related='company_id.campus_id_card_show_address', readonly=False)
    campus_id_card_show_bform = fields.Boolean(related='company_id.campus_id_card_show_bform', readonly=False)
    campus_id_card_show_emergency = fields.Boolean(related='company_id.campus_id_card_show_emergency', readonly=False)
