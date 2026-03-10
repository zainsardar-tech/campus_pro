{
    'name': 'Campus Pro Management',
    'version': '1.0',
    'summary': 'Professional Campus, School, and Institute Management System for Odoo',
    'description': """
        A complete education ERP for Pakistan-level institutes.
        - Student & Guardian Management
        - Academic Structure (Campus, Class, Section)
        - Attendance System (Manual)
        - Examination & Results
        - Fee Management & Pakistani Challan
        - WAMS WhatsApp Integration
        - OWL Dashboards
    """,
    'author': 'Zain Sardar',
    'website': 'https://zasolpk.com',
    'category': 'Education',
    'depends': ['base', 'mail', 'account', 'hr'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'data/sequence_data.xml',
        'views/academic_views.xml',
        'views/student_views.xml',
        'views/attendance_views.xml',
        'views/exam_views.xml',
        'views/finance_views.xml',
        'views/config_views.xml',
        'views/whatsapp_template_views.xml',
        'views/whatsapp_log_views.xml',
        'views/menu_views.xml',
        'wizard/whatsapp_wizard_views.xml',
        'reports/student_reports.xml',
        'reports/fee_reports.xml',
    ],
    'demo': [
        'data/demo_data.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'campus_pro/static/src/css/dashboard.css',
            'campus_pro/static/src/js/dashboard.js',
            'campus_pro/static/src/xml/dashboard.xml',
        ],
    },
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
