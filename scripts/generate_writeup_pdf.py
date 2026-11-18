"""
Generates the publication-grade 1-page writeup PDF at
D:/Placements/Projects/Marketplace_Profitability___Fulfillment_Leakage_Analysis.pdf
with zero citations, no false titles, and exact verified numbers.
"""
import os
import sys
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable, KeepTogether
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

OUTPUT_PDF = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "report", "writeup.pdf")
MASTER_PDF = r"D:\Placements\Projects\Marketplace_Profitability___Fulfillment_Leakage_Analysis.pdf"

def build_pdf():
    doc = SimpleDocTemplate(
        OUTPUT_PDF,
        pagesize=letter,
        leftMargin=36,
        rightMargin=36,
        topMargin=28,
        bottomMargin=24
    )

    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=15,
        leading=18,
        textColor=colors.HexColor('#111827'),
        alignment=1, # Center
        spaceAfter=2
    )

    repo_style = ParagraphStyle(
        'DocRepo',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor('#1D4ED8'),
        alignment=1,
        spaceAfter=3
    )

    author_style = ParagraphStyle(
        'DocAuthor',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor('#374151'),
        alignment=1,
        spaceAfter=4
    )

    h1_style = ParagraphStyle(
        'Heading1_Custom',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=10,
        leading=12,
        textColor=colors.HexColor('#0F2A4A'),
        spaceBefore=4,
        spaceAfter=2
    )

    body_style = ParagraphStyle(
        'Body_Custom',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=7.8,
        leading=10,
        textColor=colors.HexColor('#1F2937'),
        spaceAfter=2
    )

    bullet_style = ParagraphStyle(
        'Bullet_Custom',
        parent=body_style,
        leftIndent=10,
        firstLineIndent=-10,
        spaceAfter=1.5
    )

    tbl_header = ParagraphStyle(
        'TblH',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=7.5,
        leading=9.5,
        textColor=colors.HexColor('#0F2A4A')
    )

    tbl_cell = ParagraphStyle(
        'TblC',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=7.2,
        leading=9,
        textColor=colors.HexColor('#1F2937')
    )

    story = []

    # Title block
    story.append(Paragraph("Marketplace Profitability & Fulfillment Leakage Analysis", title_style))
    story.append(Paragraph("GitHub: https://github.com/Jenish1706/Marketplace-profitability-Fulfillment-Leakage-Analysis", repo_style))
    story.append(Paragraph("Jenish Patel &nbsp;|&nbsp; Operational Analytics & Unit Economics", author_style))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#0F2A4A"), spaceAfter=3, spaceBefore=0))

    # Section 1
    story.append(Paragraph("1. Executive Problem Statement", h1_style))
    story.append(Paragraph(
        "Addressing the core marketplace paradox: accelerating commercial GMV accompanied by operational friction and unit-economic compression. "
        "This diagnostic rejects black-box machine learning delay classification in favor of relational root-cause decomposition, non-parametric econometrics, "
        "controlled analytical grains, and defensible operational resource allocation across 99,441 orders.",
        body_style
    ))

    # Section 2
    story.append(Paragraph("2. Three-Level Economic Framework", h1_style))
    story.append(Paragraph(
        "To prevent fabricating unobserved platform overheads (e.g., carrier contracts, payment gateway fees, return handling costs), this diagnostic enforces a three-level framework:",
        body_style
    ))
    story.append(Paragraph(
        "• <b>Level 1: Observable Late-Order GMV & Freight:</b> Total late delivered order value <i>E</i><sub>late</sub> = R$ 1.15M "
        "(GMV R$ 985,924.34 + Freight R$ 164,967.79) across 6,534 date-level late orders (6.77% late delivery rate). Decomposed into "
        "<b>Seller-Caused Late Exposure</b> (R$ 371,281.14, 32.26%) and <b>Carrier-Caused Late Exposure</b> (R$ 779,610.99, 67.74%).",
        bullet_style
    ))
    story.append(Paragraph(
        "• <b>Level 2: Observable Cost Burden:</b> Platform Freight Burden = Total Freight / Total GMV = 16.57% (R$ 2.25M freight on R$ 13.59M GMV). "
        "High-freight exposure (≥ 30% freight-to-value ratio) encompasses R$ 1.86M GMV.",
        bullet_style
    ))
    story.append(Paragraph(
        "• <b>Level 3: Scenario-Based Economic Mitigation:</b> Modeled across prioritized seller tiers targeting seller-caused late exposure (R$ 181,377.55 in P1): "
        "Conservative 10% (R$ 18,137.76), <b>Base Case 25% (R$ 45,344.39)</b>, and Optimistic 40% (R$ 72,551.02).",
        bullet_style
    ))

    # Section 3
    story.append(Paragraph("3. Quantitative Discoveries & Econometric Evidence", h1_style))
    
    table_data = [
        [
            Paragraph("<b>Analytical Discovery</b>", tbl_header),
            Paragraph("<b>Econometric / Relational Method</b>", tbl_header),
            Paragraph("<b>Operational Evidence</b>", tbl_header)
        ],
        [
            Paragraph("<b>Decoupled Analytical Grains</b>", tbl_cell),
            Paragraph("Separate CTEs isolating order grain (99.4K) from line-item grain (112.6K)", tbl_cell),
            Paragraph("Eliminates fan-out distortion; reconciles true 97.02% delivery rate.", tbl_cell)
        ],
        [
            Paragraph("<b>Seller vs Carrier Attribution</b>", tbl_cell),
            Paragraph("Decomposed late deliveries into seller dispatch deadline vs carrier transit", tbl_cell),
            Paragraph("72.3% of late deliveries met seller dispatch limit; delay is carrier-driven.", tbl_cell)
        ],
        [
            Paragraph("<b>Review Timing Confounder</b>", tbl_cell),
            Paragraph("Evaluated review answer timestamps against delivery arrival dates", tbl_cell),
            Paragraph("70.1% of late reviews answered before arrival; binary unarrived state OR = 33.6x.", tbl_cell)
        ],
        [
            Paragraph("<b>Interstate Corridor Friction</b>", tbl_cell),
            Paragraph("Origin-destination matrix across 417 regional transit corridors", tbl_cell),
            Paragraph("SP → RJ corridor generates R$ 197K exposure (14.9% late); SP → SP operates cleanly.", tbl_cell)
        ]
    ]

    t = Table(table_data, colWidths=[130, 230, 180])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#F1F5F9')),
        ('TOPPADDING', (0, 0), (-1, -1), 2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ('RIGHTPADDING', (0, 0), (-1, -1), 4),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    story.append(t)
    story.append(Spacer(1, 2))

    # Section 4
    story.append(Paragraph("4. Deterministic Intervention Hierarchy", h1_style))
    story.append(Paragraph(
        "Rather than arbitrary weighted scoring formulas, partners are classified using transparent percentile cutoffs on volume-filtered operational sellers "
        "(<i>N</i> ≥ 30 orders) based on seller-caused dispatch delay exposure. Decile 1 holds 60.78% of GMV and 77.38% of late exposure, establishing a <b>1.27× concentration lift</b>.",
        body_style
    ))
    story.append(Paragraph(
        "• <b>P1 (Immediate Operational Intervention):</b> 113 high-volume merchants (3.65% of seller base, R$ 2.79M GMV) generating R$ 181,377.55 in seller-caused late exposure "
        "(48.85% of platform seller exposure). Targeted with mandatory 24–48hr dispatch SLAs and dynamic lead-time calibration (Base Case 25% scenario mitigation: <b>R$ 45,344.39</b>).",
        bullet_style
    ))
    story.append(Paragraph(
        "• <b>P2 (Operational Investigation):</b> 211 merchants (R$ 3.72M GMV) with elevated volume but localized failure (R$ 54,637.04 exposure).",
        bullet_style
    ))
    story.append(Paragraph(
        "• <b>P3 (Operational Monitoring):</b> 323 moderate-volume partners subject to automated threshold alerts (R$ 39,267.34 exposure).",
        bullet_style
    ))
    story.append(Paragraph(
        "• <b>P4 (Low Volume / Not Prioritised):</b> 2,448 low-volume partners (<i>N</i> &lt; 30) and standard baseline operations (R$ 95,999.21 exposure).",
        bullet_style
    ))

    doc.build(story)
    print(f"Successfully generated 1-page writeup PDF: {OUTPUT_PDF}")

if __name__ == '__main__':
    build_pdf()
