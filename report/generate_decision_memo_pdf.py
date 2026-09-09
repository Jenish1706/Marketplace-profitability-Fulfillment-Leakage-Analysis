import os
import sys
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether, HRFlowable
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfgen import canvas

class NumberedCanvas(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        super(NumberedCanvas, self).__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super(NumberedCanvas, self).showPage()
        super(NumberedCanvas, self).save()

    def draw_page_decorations(self, page_count):
        self.saveState()
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#555555"))
        # Header (pages > 1)
        if self._pageNumber > 1:
            self.drawString(40, 762, "EXECUTIVE MEMORANDUM | Marketplace Profitability & Fulfillment Leakage Diagnostic")
            self.setStrokeColor(colors.HexColor("#CCCCCC"))
            self.setLineWidth(0.5)
            self.line(40, 757, 572, 757)
        # Footer
        page_text = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(572, 25, page_text)
        self.drawString(40, 25, "CONFIDENTIAL — FOR INTERNAL EXECUTIVE LEADERSHIP USE ONLY")
        self.setStrokeColor(colors.HexColor("#CCCCCC"))
        self.setLineWidth(0.5)
        self.line(40, 35, 572, 35)
        self.restoreState()

def build_pdf():
    pdf_path = "report/decision_memo.pdf"
    doc = SimpleDocTemplate(
        pdf_path,
        pagesize=letter,
        leftMargin=40,
        rightMargin=40,
        topMargin=36,
        bottomMargin=42
    )

    styles = getSampleStyleSheet()
    
    # Custom Palette Styles
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=15,
        leading=18,
        textColor=colors.HexColor("#1A365D")
    )
    
    subtitle_style = ParagraphStyle(
        'DocSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=9,
        leading=12,
        textColor=colors.HexColor("#2B6CB0")
    )
    
    meta_style = ParagraphStyle(
        'MetaStyle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8,
        leading=11,
        textColor=colors.HexColor("#2D3748")
    )

    h1_style = ParagraphStyle(
        'H1Style',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=10,
        leading=13,
        textColor=colors.HexColor("#1A365D"),
        spaceBefore=5,
        spaceAfter=3
    )

    body_style = ParagraphStyle(
        'BodyStyle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=7.8,
        leading=10.4,
        textColor=colors.HexColor("#2D3748")
    )

    bullet_style = ParagraphStyle(
        'BulletStyle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=7.6,
        leading=10.0,
        textColor=colors.HexColor("#2D3748"),
        leftIndent=10,
        firstLineIndent=-6,
        spaceAfter=2
    )

    callout_style = ParagraphStyle(
        'CalloutStyle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=7.6,
        leading=9.8,
        textColor=colors.HexColor("#1A202C")
    )

    table_header_style = ParagraphStyle(
        'THStyle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=7.0,
        leading=8.5,
        textColor=colors.white,
        alignment=1
    )

    table_cell_style = ParagraphStyle(
        'TCStyle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=6.8,
        leading=8.2,
        textColor=colors.HexColor("#2D3748")
    )

    table_cell_center = ParagraphStyle(
        'TCCenter',
        parent=table_cell_style,
        alignment=1
    )

    table_cell_bold = ParagraphStyle(
        'TCBold',
        parent=table_cell_style,
        fontName='Helvetica-Bold'
    )

    story = []

    # ================= PAGE 1 =================
    # Memo Header Box
    story.append(Paragraph("EXECUTIVE DECISION MEMORANDUM", title_style))
    story.append(Paragraph("MARKETPLACE PROFITABILITY & FULFILLMENT LEAKAGE DIAGNOSTIC", subtitle_style))
    story.append(Spacer(1, 4))
    
    header_table_data = [
        [Paragraph("<b>TO:</b> Chief Operating Officer (COO), VP Marketplace Operations", meta_style),
         Paragraph("<b>DATE:</b> September 10, 2026", meta_style)],
        [Paragraph("<b>FROM:</b> Marketplace Commercial & Operational Analytics", meta_style),
         Paragraph("<b>SUBJECT:</b> Operational Fulfillment Leakage & Priority Interventions", meta_style)]
    ]
    t_head = Table(header_table_data, colWidths=[330, 202])
    t_head.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#EDF2F7")),
        ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor("#CBD5E0")),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor("#E2E8F0")),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
        ('RIGHTPADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(t_head)
    story.append(Spacer(1, 6))

    # Executive Summary Callout
    summary_text = (
        "<b>EXECUTIVE SUMMARY & CORE PARADOX:</b> Between Jan 2017 and Aug 2018, the platform scaled Gross Merchandise Value (GMV) "
        "from R$120K to ~R$1M monthly across 98,666 orders (R$13.59M GMV). However, top-line growth triggered severe operational friction: "
        "late deliveries spiked to <b>14.3% in Nov 2017</b> and collapsed to <b>21.4% in March 2018</b>. Overall freight burden inflated from "
        "<b>14.0% to >18.2%</b>. Fulfillment failure is strictly concentrated: <b>Top 10% of sellers generate 75.8% of platform late-order exposure</b>. "
        "By enforcing minimum volume controls, we prioritize <b>83 Priority 1 (P1) sellers</b> carrying <b>R$ 377,768.41 in late transaction exposure</b>. "
        "Under our Base Case recovery model (25% addressable mitigation), targeted operations account management unlocks <b>R$ 94,442.10</b> in recoverable economic value."
    )
    t_sum = Table([[Paragraph(summary_text, callout_style)]], colWidths=[532])
    t_sum.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#EBF8FF")),
        ('BOX', (0,0), (-1,-1), 1.0, colors.HexColor("#3182CE")),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ('LEFTPADDING', (0,0), (-1,-1), 8),
        ('RIGHTPADDING', (0,0), (-1,-1), 8),
    ]))
    story.append(t_sum)
    story.append(Spacer(1, 6))

    # KPI Scorecard Ribbon
    kpi_data = [
        [Paragraph("<b>TOTAL GMV</b>", table_cell_center),
         Paragraph("<b>ORDERS</b>", table_cell_center),
         Paragraph("<b>LATE RATE</b>", table_cell_center),
         Paragraph("<b>FREIGHT BURDEN</b>", table_cell_center),
         Paragraph("<b>AVG REVIEW</b>", table_cell_center),
         Paragraph("<b>LATE EXPOSURE</b>", table_cell_center)],
        [Paragraph("<b>R$ 13.59M</b>", table_cell_center),
         Paragraph("<b>98,666</b>", table_cell_center),
         Paragraph("<b>7.91%</b>", table_cell_center),
         Paragraph("<b>16.57%</b>", table_cell_center),
         Paragraph("<b>4.03 / 5.0</b>", table_cell_center),
         Paragraph("<b>R$ 1.35M</b>", table_cell_center)]
    ]
    t_kpi = Table(kpi_data, colWidths=[88, 88, 88, 88, 88, 102])
    t_kpi.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#2B6CB0")),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('BACKGROUND', (0,1), (-1,1), colors.HexColor("#F7FAFC")),
        ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor("#CBD5E0")),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor("#CBD5E0")),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
    ]))
    story.append(t_kpi)
    story.append(Spacer(1, 6))

    # Section 1: Macro Performance Trends
    story.append(Paragraph("1. Macro Performance Inflection: Growth vs Operational Breakdown", h1_style))
    story.append(Paragraph(
        "Monthly diagnostic tracking identifies clear operational stress inflection points where fulfillment broke down:",
        body_style
    ))
    story.append(Paragraph("• <b>Black Friday Surge (Nov 2017):</b> Orders surged +63% MoM (7,544 orders), overwhelming carrier networks and driving late delivery rate to <b>14.31%</b> (R$ 168.9K exposed transaction value).", bullet_style))
    story.append(Paragraph("• <b>Q1 2018 Fulfillment Crisis:</b> Rather than normalizing post-holiday, late delivery rates spiked to <b>15.99% in Feb</b> and peaked at <b>21.36% in March 2018</b>. Late shipments incurred an average delay of <b>+8.87 days</b> beyond customer commitments.", bullet_style))
    story.append(Paragraph("• <b>Freight Cost Inflation:</b> Platform freight burden escalated from 14.03% in Jan 2017 to over <b>18.23% by mid-2018</b>, proving that logistics cost growth significantly outpaced merchandise revenue.", bullet_style))
    story.append(Spacer(1, 5))

    # Section 2: Root-Cause Decomposition
    story.append(Paragraph("2. Multi-Dimensional Root-Cause Decomposition", h1_style))
    story.append(Paragraph(
        "Operational failure is driven by three distinct structural mechanisms:",
        body_style
    ))
    story.append(Paragraph(
        "• <b>Volume × Severity Decoupling:</b> Uncontrolled rankings misallocate resources by flagging low-volume sellers with 100% failure rates (e.g., 2 orders, R$72 exposure). Real business liability is concentrated in high-volume sellers: the top exposed seller (<code>4a3ca93a...</code>) processed 1,806 orders with a 16.0% late rate, generating <b>R$ 29,420.57 in late exposure</b> alone.",
        bullet_style
    ))
    story.append(Paragraph(
        "• <b>Product Category Logistics Deficits:</b> Categories with heavy/bulky physical profiles (<code>furniture_decor</code>, <code>office_furniture</code>, <code>bed_bath_table</code>) carry structural freight burdens of <b>25% to 35%</b>, with high freight-per-kg ratios eroding merchant and platform unit economics.",
        bullet_style
    ))
    story.append(Paragraph(
        "• <b>Inter-State Corridor Friction:</b> Local intra-state deliveries (SP → SP) run efficiently (5.5% late rate, 12% freight burden). Conversely, long-haul cross-regional lanes (SP → RJ, SP → BA, SP → MG) suffer acute logistical strain: the SP → RJ corridor alone generates <b>R$ 138K in late exposure</b> with an 11.2% late delivery rate.",
        bullet_style
    ))

    # Force Page Break to guarantee exactly 2 pages
    story.append(PageBreak())

    # ================= PAGE 2 =================
    story.append(Paragraph("3. Pareto Concentration & Intervention Prioritization Framework", h1_style))
    story.append(Paragraph(
        "Cumulative window analysis demonstrates extreme Pareto concentration: <b>Top 10% of sellers (310 sellers) account for 75.83% of late-order exposure</b>, while the bottom 50% have zero late items. Applying deterministic percentile thresholds across operational sellers ($N \\ge 30$) isolates four actionable tiers:",
        body_style
    ))
    story.append(Spacer(1, 3))

    tier_table_data = [
        [Paragraph("<b>Priority Tier</b>", table_header_style),
         Paragraph("<b>Sellers</b>", table_header_style),
         Paragraph("<b>% Base</b>", table_header_style),
         Paragraph("<b>Orders</b>", table_header_style),
         Paragraph("<b>GMV (R$)</b>", table_header_style),
         Paragraph("<b>Late Exposure (R$)</b>", table_header_style),
         Paragraph("<b>% Exp</b>", table_header_style),
         Paragraph("<b>Operational Action Playbook</b>", table_header_style)],
        
        [Paragraph("<b>P1 — Immediate Intervention</b>", table_cell_bold),
         Paragraph("83", table_cell_center),
         Paragraph("2.68%", table_cell_center),
         Paragraph("19,046", table_cell_center),
         Paragraph("R$ 2.35M", table_cell_center),
         Paragraph("<b>R$ 377,768.41</b>", table_cell_bold),
         Paragraph("<b>27.95%</b>", table_cell_bold),
         Paragraph("Mandatory 24-hr dispatch SLA, dynamic EDD recalibration, packaging audit", table_cell_style)],

        [Paragraph("<b>P2 — Operational Investigation</b>", table_cell_style),
         Paragraph("272", table_cell_center),
         Paragraph("8.79%", table_cell_center),
         Paragraph("43,025", table_cell_center),
         Paragraph("R$ 5.30M", table_cell_center),
         Paragraph("R$ 504,623.53", table_cell_style),
         Paragraph("37.33%", table_cell_center),
         Paragraph("Carrier dispatch audit, lane-specific carrier re-allocation", table_cell_style)],

        [Paragraph("<b>P3 — Operational Monitoring</b>", table_cell_style),
         Paragraph("149", table_cell_center),
         Paragraph("4.81%", table_cell_center),
         Paragraph("10,962", table_cell_center),
         Paragraph("R$ 1.55M", table_cell_center),
         Paragraph("R$ 153,332.79", table_cell_style),
         Paragraph("11.34%", table_cell_center),
         Paragraph("Automated portal threshold warnings; 30-day monitoring window", table_cell_style)],

        [Paragraph("<b>P4 — Standard Governance</b>", table_cell_style),
         Paragraph("2,591", table_cell_center),
         Paragraph("83.72%", table_cell_center),
         Paragraph("26,977", table_cell_center),
         Paragraph("R$ 4.39M", table_cell_center),
         Paragraph("R$ 315,900.23", table_cell_style),
         Paragraph("23.37%", table_cell_center),
         Paragraph("Routine partner management; healthy performance benchmark", table_cell_style)]
    ]
    t_tier = Table(tier_table_data, colWidths=[105, 30, 32, 38, 52, 68, 35, 172])
    t_tier.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#1A365D")),
        ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor("#CBD5E0")),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor("#E2E8F0")),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.HexColor("#FFF5F5"), colors.HexColor("#FFFAF0"), colors.white, colors.white]),
        ('TOPPADDING', (0,0), (-1,-1), 2.5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2.5),
        ('LEFTPADDING', (0,0), (-1,-1), 3),
        ('RIGHTPADDING', (0,0), (-1,-1), 3),
    ]))
    story.append(t_tier)
    story.append(Spacer(1, 5))

    # Section 4: Addressable Economic Exposure & Sensitivity
    story.append(Paragraph("4. Quantified Addressable Recovery & Scenario Modeling", h1_style))
    story.append(Paragraph(
        "We distinguish strictly between <b>observable transaction exposure</b> and <b>scenario-based recoverable economic exposure</b>. Total platform late exposure is R$ 1.35M. Focusing operations exclusively on the 83 P1 sellers yields the following addressable recovery ranges:",
        body_style
    ))
    
    scenario_data = [
        [Paragraph("<b>Recovery Scenario</b>", table_header_style),
         Paragraph("<b>Assumed Recovery Rate</b>", table_header_style),
         Paragraph("<b>Target Cohort</b>", table_header_style),
         Paragraph("<b>Late Exposure Managed</b>", table_header_style),
         Paragraph("<b>Addressable Recoverable Value</b>", table_header_style)],
        [Paragraph("<b>Conservative Case</b>", table_cell_bold),
         Paragraph("10% Addressable Mitigation", table_cell_center),
         Paragraph("P1 Sellers (83)", table_cell_center),
         Paragraph("R$ 377,768.41", table_cell_center),
         Paragraph("<b>R$ 37,776.84</b>", table_cell_bold)],
        [Paragraph("<b>Base Case (Target)</b>", table_cell_bold),
         Paragraph("25% Addressable Mitigation", table_cell_center),
         Paragraph("P1 Sellers (83)", table_cell_center),
         Paragraph("R$ 377,768.41", table_cell_center),
         Paragraph("<b>R$ 94,442.10</b>", table_cell_bold)],
        [Paragraph("<b>Optimistic Case</b>", table_cell_bold),
         Paragraph("40% Addressable Mitigation", table_cell_center),
         Paragraph("P1 Sellers (83)", table_cell_center),
         Paragraph("R$ 377,768.41", table_cell_center),
         Paragraph("<b>R$ 151,107.36</b>", table_cell_bold)]
    ]
    t_scen = Table(scenario_data, colWidths=[105, 95, 75, 110, 147])
    t_scen.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#2B6CB0")),
        ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor("#CBD5E0")),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor("#E2E8F0")),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.HexColor("#F7FAFC"), colors.HexColor("#EDF2F7"), colors.HexColor("#F7FAFC")]),
        ('TOPPADDING', (0,0), (-1,-1), 2.5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2.5),
    ]))
    story.append(t_scen)
    story.append(Spacer(1, 4))
    story.append(Paragraph(
        "<i>Volume Cutoff Sensitivity:</i> $N \\ge 20$ yields 104 P1 sellers (R$ 415.6K exposure); $N \\ge 50$ yields 51 sellers (R$ 314.4K exposure). The baseline $N \\ge 30$ captures 83 sellers controlling 28% of platform exposure, balancing operational capacity against yield.",
        body_style
    ))
    story.append(Spacer(1, 5))

    # Section 5: Statistical Validation
    story.append(Paragraph("5. Statistical Validation & Customer Experience Impact", h1_style))
    story.append(Paragraph(
        "Non-parametric hypothesis testing proves customer sentiment is severely degraded by delivery delays. Baseline on-time orders average <b>4.29 / 5.00</b> (6.6% low reviews $\\le 2$ stars). Ratings collapse to <b>3.77</b> (1-2 days late), <b>2.47</b> (3-5 days late, 48.4% low reviews), and <b>1.74</b> (>5 days late, 68.6% low reviews). Kruskal-Wallis test ($H = 10,316.6, p < 10^{-15}$) and Mann-Whitney U ($r = -0.76$) confirm statistical significance. Multivariate logistic regression demonstrates delivery delay is the dominant predictor of poor ratings ($\text{OR} = 1.047 \text{ per delay day}, p < 0.001$), controlling for item price and freight ratio.",
        body_style
    ))
    story.append(Spacer(1, 5))

    # Section 6: Action Recommendations & Governance
    story.append(Paragraph("6. Prioritized Management Action Plan & Governance", h1_style))
    story.append(Paragraph("1. <b>Deploy Partner Ops to 83 P1 Sellers:</b> Establish dedicated account remediation, enforce 24-hour dispatch cutoffs, and dynamically adjust platform EDD buffers.", bullet_style))
    story.append(Paragraph("2. <b>Restructure Heavy/Bulky Category Logistics:</b> Eliminate flat freight subsidies on categories with freight burden >25% (furniture, bedding); introduce volumetric shipping tiers.", bullet_style))
    story.append(Paragraph("3. <b>Corridor Routing Consolidation (SP → RJ / BA):</b> Shift long-haul inter-state volume to regional 3PL consolidation hubs, avoiding postal bottlenecks.", bullet_style))
    story.append(Spacer(1, 4))

    # Methodological Integrity Footnote Box
    method_text = (
        "<b>METHODOLOGICAL INTEGRITY NOTE:</b> The Olist dataset records observed item prices, freight values, and delivery timestamps, but lacks unobserved "
        "cost fields (seller commissions, payment processing fees, carrier contract settlements, reverse logistics). Accordingly, exposure metrics reflect "
        "observable transaction value, not realized company profit loss. Addressable recovery values represent deterministic scenario models, not speculative accounting claims."
    )
    t_method = Table([[Paragraph(method_text, callout_style)]], colWidths=[532])
    t_method.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#F7FAFC")),
        ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor("#A0AEC0")),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
        ('RIGHTPADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(t_method)

    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"Successfully generated publication-grade PDF: {pdf_path}")

if __name__ == "__main__":
    build_pdf()
