# 🎓 Campus Pro Management

**Campus Pro** is a comprehensive, professional Education ERP designed specifically for schools, colleges, and training institutes. Built on Odoo 18, it streamlines administrative tasks, enhances communication via WhatsApp, and provides deep academic intelligence.

---

## 🌟 Key Features

### 🏢 Multi-Campus Management
- Manage multiple institute branches under one system.
- Scope templates and records to specific campuses.

### 👥 Student & Guardian Portal
- Detailed student profiles with GR numbers and registration tracking.
- Securely store parent/guardian contact information.
- Pakistani format normalization for phone numbers and CNICs.

### 📅 Academic Operations
- **Attendance**: Track daily presence with automated absence notifications.
- **Academics**: Flexible Class, Section, and Session management.
- **Examination**: Create exams, publish results, and track historical performance.

### 💰 Finance & Fee Management
- **Pakistani Challan System**: Custom-designed fee challans with partial payment support.
- **Fine Rules**: Automated late fee calculations (Fixed or Per Day).
- **Collection Dashboards**: Real-time insights into paid vs. unpaid dues.

### 🛡️ Smart WhatsApp Integration (WAMS Powered)
Our governing messaging system ensures professional, auditable, and spam-free communication:
- **Trigger Matrix**: Configure events (Admission, Absence, Fees) to trigger messages automatically or manually.
- **Template Approval Flow**: Admins must approve templates before they can be used.
- **Audit Logs**: Every message attempt is logged with status tracking and failure reasons.
- **Validation**: Automatically blocks messaging for struck-off or inactive students.

### 📊 Intelligence Center
Modern OWL-based dashboard providing:
- **Dropout Risk Analysis**: Identify at-risk students based on attendance patterns.
- **Exam Eligibility Tracker**: Automatic checks against attendance thresholds.
- **Interactive Drill-downs**: Click any stat to see the filtered list of students or challans.

---

## 🛠️ Technical Stack
- **Framework**: Odoo 18 (LGPL)
- **Frontend**: OWL (Odoo Web Library), Chart.js, HTML5 Canvas
- **Backend**: Python 3.10+, PostgreSQL
- **Integrations**: WAMS API (WhatsApp API Gateway)
- **UI/UX**: Custom CSS (Glassmorphism design)

---

## 🚀 Installation

1. **Clone the repository** into your Odoo custom addons directory.
2. **Install Dependencies**:
   ```bash
   pip install qrcode base64 requests
   ```
3. **Update Module List**: Log in to Odoo with Developer Mode, go to **Apps**, and click **Update Apps List**.
4. **Install**: Search for `campus_pro` and click **Install**.

---

## ⚙️ Configuration

1. **WhatsApp Integration**:
   - Go to **Campus Pro > Configuration > Settings**.
   - Input your **WAMS API Key** and **Sender Number**.
   - Use the **Test Connection** button to verify connectivity.
2. **Trigger Matrix**:
   - Navigate to **WhatsApp Automation > Trigger Matrix**.
   - Select which events should send automatically (e.g., Absence) or manually (e.g., Fee Reminders).
3. **Templates**:
   - Go to **Message Templates** and create your content using `{{student.name}}` placeholders.
   - An Administrator must check the **Approved?** box for each template.

---

## 📝 Authors & Support
- **Author**: Zain Sardar
- **Website**: [zasolpk.com](https://zasolpk.com)
- **License**: LGPL-3

---

> [!TIP]
> **Pro Tip**: Use the **Silent Mode** in the Trigger Matrix to log message intents during testing without burning your WhatsApp API credits!
