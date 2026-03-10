/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, onWillStart, onMounted, useRef } from "@odoo/owl";
import { loadJS } from "@web/core/assets";

export class AcademyDashboard extends Component {
    static template = "campus_pro.DashboardMain";

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");

        this.trendsChartRef = useRef("trendsChart");
        this.dailyTrendsChartRef = useRef("dailyTrendsChart");
        this.classDistChartRef = useRef("classDistChart");
        this.feeChartRef = useRef("feeChart");
        this.genderChartRef = useRef("genderChart");

        this.state = {
            stats: {
                students: 0,
                attendance_today: 0,
                fees_collected: 0,
                fees_total: 0,
                defaulters: 0,
                wams_connected: false,
                high_risk_count: 0,
                ineligible_count: 0,
                trends: { labels: [], data: [] },
                daily_trends: { labels: [], data: [] },
                class_dist: { labels: [], data: [] },
                gender_dist: { labels: [], data: [] },
                fee_stats: { paid: 0, unpaid: 0 },
                recent_students: []
            }
        };

        onWillStart(async () => {
            await loadJS("/web/static/lib/Chart/Chart.js");
            await this.fetchStats();
        });

        onMounted(() => {
            this.renderCharts();
        });
    }

    async fetchStats() {
        const result = await this.orm.call("campus.student", "get_dashboard_stats", []);

        // Pre-format data for the template
        if (result.recent_students) {
            result.recent_students = result.recent_students.map(s => ({
                ...s,
                formatted_id: String(s.id).padStart(5, '0'),
                formatted_date: new Date(s.create_date).toLocaleDateString()
            }));
        }

        this.state.stats = result;
    }

    renderCharts() {
        const commonOptions = {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: {
                        font: { family: "'Outfit', sans-serif", size: 11 },
                        padding: 15,
                        usePointStyle: true
                    }
                },
                tooltip: {
                    backgroundColor: 'rgba(30, 41, 59, 0.9)',
                    titleFont: { family: "'Outfit', sans-serif", size: 14 },
                    bodyFont: { family: "'Outfit', sans-serif", size: 12 },
                    padding: 12,
                    cornerRadius: 8
                }
            }
        };

        // Enrollment Trends (Line Chart - Monthly)
        if (this.trendsChartRef.el) {
            new Chart(this.trendsChartRef.el, {
                type: 'line',
                data: {
                    labels: this.state.stats.trends.labels,
                    datasets: [{
                        label: 'Monthly Admissions',
                        data: this.state.stats.trends.data,
                        borderColor: '#6366f1',
                        backgroundColor: 'rgba(99, 102, 241, 0.1)',
                        fill: true,
                        tension: 0.4,
                        pointRadius: 4
                    }]
                },
                options: {
                    ...commonOptions,
                    scales: {
                        y: { beginAtZero: true, grid: { color: 'rgba(0,0,0,0.05)' } },
                        x: { grid: { display: false } }
                    }
                }
            });
        }

        // Daily Admissions (Bar Chart)
        if (this.dailyTrendsChartRef.el) {
            new Chart(this.dailyTrendsChartRef.el, {
                type: 'bar',
                data: {
                    labels: this.state.stats.daily_trends.labels,
                    datasets: [{
                        label: 'Daily Admissions',
                        data: this.state.stats.daily_trends.data,
                        backgroundColor: '#818cf8',
                        borderRadius: 6
                    }]
                },
                options: {
                    ...commonOptions,
                    scales: {
                        y: { beginAtZero: true, grid: { borderDash: [5, 5] } },
                        x: { grid: { display: false } }
                    }
                }
            });
        }

        // Class Distribution (Bar Chart)
        if (this.classDistChartRef.el) {
            new Chart(this.classDistChartRef.el, {
                type: 'bar',
                data: {
                    labels: this.state.stats.class_dist.labels,
                    datasets: [{
                        label: 'Students',
                        data: this.state.stats.class_dist.data,
                        backgroundColor: '#0ea5e9',
                        borderRadius: 6
                    }]
                },
                options: {
                    ...commonOptions,
                    indexAxis: 'y',
                    scales: {
                        x: { beginAtZero: true, grid: { display: false } },
                        y: { grid: { display: false } }
                    }
                }
            });
        }

        // Gender Distribution (Doughnut)
        if (this.genderChartRef.el) {
            new Chart(this.genderChartRef.el, {
                type: 'doughnut',
                data: {
                    labels: this.state.stats.gender_dist.labels,
                    datasets: [{
                        data: this.state.stats.gender_dist.data,
                        backgroundColor: ['#6366f1', '#f472b6', '#94a3b8'],
                        borderWidth: 0
                    }]
                },
                options: {
                    ...commonOptions,
                    cutout: '65%'
                }
            });
        }

        // Fee Stats (Pie Chart)
        if (this.feeChartRef.el) {
            new Chart(this.feeChartRef.el, {
                type: 'pie',
                data: {
                    labels: ['Paid', 'Unpaid'],
                    datasets: [{
                        data: [this.state.stats.fee_stats.paid, this.state.stats.fee_stats.unpaid],
                        backgroundColor: ['#10b981', '#ef4444'],
                        borderWidth: 0
                    }]
                },
                options: commonOptions
            });
        }
    }

    onWamsClick() {
        this.action.doAction("campus_pro.action_campus_config_settings");
    }

    onStudentClick() {
        this.action.doAction("campus_pro.action_campus_student");
    }

    onFeesClick() {
        this.action.doAction("campus_pro.action_campus_fee_challan");
    }

    onDefaultersClick() {
        this.action.doAction({
            name: "Fee Defaulters",
            type: "ir.actions.act_window",
            res_model: "campus.fee.challan",
            views: [[false, "list"], [false, "form"]],
            domain: [['state', '!=', 'paid'], ['date_due', '<', new Date().toISOString().split('T')[0]]],
            target: "current",
        });
    }

    onAttendanceClick() {
        this.action.doAction({
            name: "Today's Attendance",
            type: "ir.actions.act_window",
            res_model: "campus.attendance",
            views: [[false, "list"], [false, "form"]],
            domain: [['date', '=', new Date().toISOString().split('T')[0]]],
            target: "current",
        });
    }

    onRiskClick() {
        this.action.doAction({
            name: "High Risk Students",
            type: "ir.actions.act_window",
            res_model: "campus.student",
            views: [[false, "list"], [false, "form"]],
            domain: [['dropout_risk', 'in', ['medium', 'high']]],
            target: "current",
        });
    }

    onEligibilityClick() {
        this.action.doAction({
            name: "Ineligible Students",
            type: "ir.actions.act_window",
            res_model: "campus.student",
            views: [[false, "list"], [false, "form"]],
            domain: [['exam_eligibility', '=', false], ['state', '=', 'enrolled']],
            target: "current",
        });
    }
}

registry.category("actions").add("campus_dashboard_tag", AcademyDashboard);
