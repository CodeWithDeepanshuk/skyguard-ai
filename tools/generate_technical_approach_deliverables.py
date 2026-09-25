"""Generate redesigned TECHNICAL APPROACH deliverables for SIH Problem Statement 26073.
Outputs:
  - sih26073_technical_approach.svg
  - sih26073_technical_approach.html (for high-fidelity rendering)
  - sih26073_technical_approach.png (rendered at 1920x1080 via headless Edge)
  - sih26073_technical_approach.pptx (editable slide with native PowerPoint shapes & text)
"""

import os
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.enum.shapes import MSO_SHAPE

def create_pptx():
    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    slide = prs.slides.add_slide(prs.slide_layouts[6]) # blank layout

    # Colors
    c_navy = RGBColor(10, 37, 64)       # #0A2540
    c_slate = RGBColor(71, 85, 105)     # #475569
    c_dark = RGBColor(15, 23, 42)       # #0F172A
    c_teal_bg = RGBColor(240, 253, 250) # #F0FDFA
    c_teal_br = RGBColor(13, 148, 136)  # #0D9488
    c_teal_txt = RGBColor(15, 118, 110) # #0F766E
    c_green_bg = RGBColor(240, 253, 244)# #F0FDF4
    c_green_br = RGBColor(22, 163, 74)  # #16A34A
    c_green_txt = RGBColor(21, 128, 61) # #15803D
    c_red_bg = RGBColor(254, 242, 242)  # #FEF2F2
    c_red_br = RGBColor(220, 38, 38)    # #DC2626
    c_red_txt = RGBColor(185, 28, 28)   # #B91C1C
    c_amber_bg = RGBColor(254, 243, 199)# #FEF3C7
    c_amber_br = RGBColor(217, 119, 6)  # #D97706
    c_amber_txt = RGBColor(180, 83, 9)  # #B45309
    c_card_bg = RGBColor(248, 250, 252) # #F8FAFC
    c_border = RGBColor(203, 213, 225)  # #CBD5E1

    # Header
    tx_box = slide.shapes.add_textbox(Inches(0.6), Inches(0.35), Inches(12.1), Inches(0.8))
    tf = tx_box.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_top = tf.margin_right = tf.margin_bottom = 0
    
    p1 = tf.paragraphs[0]
    p1.text = "TECHNICAL APPROACH"
    p1.font.bold = True
    p1.font.size = Pt(26)
    p1.font.color.rgb = c_navy
    p1.font.name = "Arial"

    p2 = tf.add_paragraph()
    p2.text = "From weather readings to explainable sensor alerts  •  SIH Problem Statement 26073"
    p2.font.size = Pt(12)
    p2.font.color.rgb = c_slate
    p2.font.name = "Arial"

    # Left Panel: 3 Short Explanations (approx 25% width)
    panel = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.6), Inches(1.25), Inches(3.2), Inches(4.9))
    panel.fill.solid()
    panel.fill.fore_color.rgb = c_card_bg
    panel.line.color.rgb = c_border
    panel.line.width = Pt(1)

    ptf = panel.text_frame
    ptf.word_wrap = True
    ptf.margin_left = ptf.margin_right = Inches(0.2)
    ptf.margin_top = ptf.margin_bottom = Inches(0.18)

    # Explanation 1
    ep1 = ptf.paragraphs[0]
    ep1.text = "1. Collect and check readings"
    ep1.font.bold = True
    ep1.font.size = Pt(13)
    ep1.font.color.rgb = c_navy

    ep1_sub = ptf.add_paragraph()
    ep1_sub.text = "Ingests temperature, atmospheric pressure, and humidity observations. Preserves original raw readings while applying physical bounds, rate-of-change, and transmission gap checks."
    ep1_sub.font.size = Pt(10)
    ep1_sub.font.color.rgb = c_slate
    ep1_sub.space_after = Pt(14)

    # Explanation 2
    ep2 = ptf.add_paragraph()
    ep2.text = "2. Compare history and nearby stations"
    ep2.font.bold = True
    ep2.font.size = Pt(13)
    ep2.font.color.rgb = c_navy

    ep2_sub = ptf.add_paragraph()
    ep2_sub.text = "Evaluates temporal sequence dynamics (sudden jumps, stuck readings, slow drift) and compares nearby peer stations with location and elevation adjustments where implemented."
    ep2_sub.font.size = Pt(10)
    ep2_sub.font.color.rgb = c_slate
    ep2_sub.space_after = Pt(14)

    # Explanation 3
    ep3 = ptf.add_paragraph()
    ep3.text = "3. Explain alerts to operators"
    ep3.font.bold = True
    ep3.font.size = Pt(13)
    ep3.font.color.rgb = c_navy

    ep3_sub = ptf.add_paragraph()
    ep3_sub.text = "Distinguishes regional synoptic weather movements from isolated sensor failure. Dispatches operator alerts with root-cause reasons and clearly labelled estimated readings."
    ep3_sub.font.size = Pt(10)
    ep3_sub.font.color.rgb = c_slate

    # Right Main Flow (approx 75% width)
    x_flow = Inches(4.1)
    w_main = Inches(8.6)
    
    # Box 1: Collect Weather Readings
    b1 = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, x_flow, Inches(1.25), w_main, Inches(0.58))
    b1.fill.solid()
    b1.fill.fore_color.rgb = c_teal_bg
    b1.line.color.rgb = c_teal_br
    b1.line.width = Pt(1.5)
    tf1 = b1.text_frame
    tf1.word_wrap = True
    tf1.margin_top = tf1.margin_bottom = Inches(0.04)
    p = tf1.paragraphs[0]
    p.text = "1. Collect Weather Readings"
    p.font.bold = True
    p.font.size = Pt(12)
    p.font.color.rgb = c_teal_txt
    p.alignment = PP_ALIGN.CENTER
    p_sub = tf1.add_paragraph()
    p_sub.text = "Temperature  •  Pressure  •  Humidity   (Connected weather-station data sources)"
    p_sub.font.size = Pt(10)
    p_sub.font.color.rgb = c_slate
    p_sub.alignment = PP_ALIGN.CENTER

    # Box 2: Check Data Quality
    b2 = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, x_flow, Inches(2.0), w_main, Inches(0.58))
    b2.fill.solid()
    b2.fill.fore_color.rgb = c_teal_bg
    b2.line.color.rgb = c_teal_br
    b2.line.width = Pt(1.5)
    tf2 = b2.text_frame
    tf2.word_wrap = True
    tf2.margin_top = tf2.margin_bottom = Inches(0.04)
    p = tf2.paragraphs[0]
    p.text = "2. Check Data Quality"
    p.font.bold = True
    p.font.size = Pt(12)
    p.font.color.rgb = c_teal_txt
    p.alignment = PP_ALIGN.CENTER
    p_sub = tf2.add_paragraph()
    p_sub.text = "Missing readings  •  Wrong values  •  Time gaps   (Preserve original readings and attach quality flags)"
    p_sub.font.size = Pt(10)
    p_sub.font.color.rgb = c_slate
    p_sub.alignment = PP_ALIGN.CENTER

    # Box 3: Detect Unusual Patterns
    b3 = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, x_flow, Inches(2.75), w_main, Inches(0.58))
    b3.fill.solid()
    b3.fill.fore_color.rgb = c_teal_bg
    b3.line.color.rgb = c_teal_br
    b3.line.width = Pt(1.5)
    tf3 = b3.text_frame
    tf3.word_wrap = True
    tf3.margin_top = tf3.margin_bottom = Inches(0.04)
    p = tf3.paragraphs[0]
    p.text = "3. Detect Unusual Patterns"
    p.font.bold = True
    p.font.size = Pt(12)
    p.font.color.rgb = c_teal_txt
    p.alignment = PP_ALIGN.CENTER
    p_sub = tf3.add_paragraph()
    p_sub.text = "Sudden jumps  •  Stuck readings  •  Slow drift   (AI models and basic quality checks examine current & past readings)"
    p_sub.font.size = Pt(10)
    p_sub.font.color.rgb = c_slate
    p_sub.alignment = PP_ALIGN.CENTER

    # Box 4: Check Supporting Evidence
    b4 = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, x_flow, Inches(3.5), w_main, Inches(0.58))
    b4.fill.solid()
    b4.fill.fore_color.rgb = c_teal_bg
    b4.line.color.rgb = c_teal_br
    b4.line.width = Pt(1.5)
    tf4 = b4.text_frame
    tf4.word_wrap = True
    tf4.margin_top = tf4.margin_bottom = Inches(0.04)
    p = tf4.paragraphs[0]
    p.text = "4. Check Supporting Evidence"
    p.font.bold = True
    p.font.size = Pt(12)
    p.font.color.rgb = c_teal_txt
    p.alignment = PP_ALIGN.CENTER
    p_sub = tf4.add_paragraph()
    p_sub.text = "Station history  •  Nearby stations   (Compare suitable nearby stations, accounting for location & elevation)"
    p_sub.font.size = Pt(10)
    p_sub.font.color.rgb = c_slate
    p_sub.alignment = PP_ALIGN.CENTER

    # Step 5: Three Decision Branches Side by Side
    w_branch = Inches(2.72)
    gap_branch = Inches(0.22)
    y_branch = Inches(4.25)
    h_branch = Inches(0.85)

    # Branch 1: Likely Real Weather (Green)
    x1 = x_flow
    br1 = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, x1, y_branch, w_branch, h_branch)
    br1.fill.solid()
    br1.fill.fore_color.rgb = c_green_bg
    br1.line.color.rgb = c_green_br
    br1.line.width = Pt(1.5)
    tbr1 = br1.text_frame
    tbr1.word_wrap = True
    tbr1.margin_top = tbr1.margin_bottom = Inches(0.05)
    p = tbr1.paragraphs[0]
    p.text = "Likely Real Weather"
    p.font.bold = True
    p.font.size = Pt(11)
    p.font.color.rgb = c_green_txt
    p.alignment = PP_ALIGN.CENTER
    p_sub = tbr1.add_paragraph()
    p_sub.text = "Similar changes nearby\n(Weather Advisory)"
    p_sub.font.size = Pt(9.5)
    p_sub.font.color.rgb = c_dark
    p_sub.alignment = PP_ALIGN.CENTER

    # Branch 2: Suspected Sensor Fault (Red)
    x2 = x1 + w_branch + gap_branch
    br2 = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, x2, y_branch, w_branch, h_branch)
    br2.fill.solid()
    br2.fill.fore_color.rgb = c_red_bg
    br2.line.color.rgb = c_red_br
    br2.line.width = Pt(1.5)
    tbr2 = br2.text_frame
    tbr2.word_wrap = True
    tbr2.margin_top = tbr2.margin_bottom = Inches(0.05)
    p = tbr2.paragraphs[0]
    p.text = "Suspected Sensor Fault"
    p.font.bold = True
    p.font.size = Pt(11)
    p.font.color.rgb = c_red_txt
    p.alignment = PP_ALIGN.CENTER
    p_sub = tbr2.add_paragraph()
    p_sub.text = "Unusual station behaviour\n(Confirmed by persistence & fault evidence)"
    p_sub.font.size = Pt(9.5)
    p_sub.font.color.rgb = c_dark
    p_sub.alignment = PP_ALIGN.CENTER

    # Branch 3: Needs Review (Amber)
    x3 = x2 + w_branch + gap_branch
    br3 = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, x3, y_branch, w_branch, h_branch)
    br3.fill.solid()
    br3.fill.fore_color.rgb = c_amber_bg
    br3.line.color.rgb = c_amber_br
    br3.line.width = Pt(1.5)
    tbr3 = br3.text_frame
    tbr3.word_wrap = True
    tbr3.margin_top = tbr3.margin_bottom = Inches(0.05)
    p = tbr3.paragraphs[0]
    p.text = "Needs Review"
    p.font.bold = True
    p.font.size = Pt(11)
    p.font.color.rgb = c_amber_txt
    p.alignment = PP_ALIGN.CENTER
    p_sub = tbr3.add_paragraph()
    p_sub.text = "Insufficient or conflicting evidence\n(Uncertain cases not marked healthy)"
    p_sub.font.size = Pt(9.5)
    p_sub.font.color.rgb = c_dark
    p_sub.alignment = PP_ALIGN.CENTER

    # Optional Feature Box: Maintenance Support
    b_maint = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, x_flow, Inches(5.23), w_main, Inches(0.42))
    b_maint.fill.solid()
    b_maint.fill.fore_color.rgb = RGBColor(248, 250, 252)
    b_maint.line.color.rgb = RGBColor(203, 213, 225)
    b_maint.line.width = Pt(1)
    tmf = b_maint.text_frame
    tmf.word_wrap = True
    tmf.margin_top = tmf.margin_bottom = Inches(0.02)
    pm = tmf.paragraphs[0]
    pm.text = "Maintenance Support — fault explanation and clearly labelled estimated readings (original records preserved)"
    pm.font.size = Pt(9)
    pm.font.color.rgb = c_slate
    pm.alignment = PP_ALIGN.CENTER

    # Box 6: Operator Dashboard
    b6 = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, x_flow, Inches(5.75), w_main, Inches(0.6))
    b6.fill.solid()
    b6.fill.fore_color.rgb = c_teal_bg
    b6.line.color.rgb = c_teal_br
    b6.line.width = Pt(1.5)
    tf6 = b6.text_frame
    tf6.word_wrap = True
    tf6.margin_top = tf6.margin_bottom = Inches(0.04)
    p = tf6.paragraphs[0]
    p.text = "6. Operator Dashboard"
    p.font.bold = True
    p.font.size = Pt(12)
    p.font.color.rgb = c_teal_txt
    p.alignment = PP_ALIGN.CENTER
    p_sub = tf6.add_paragraph()
    p_sub.text = "Station map  •  Reading trends  •  Alerts with reasons   (Displays weather advisories, suspected faults, & reviews)"
    p_sub.font.size = Pt(10)
    p_sub.font.color.rgb = c_slate
    p_sub.alignment = PP_ALIGN.CENTER

    # Technology Footer
    b_tech = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.6), Inches(6.5), Inches(12.1), Inches(0.65))
    b_tech.fill.solid()
    b_tech.fill.fore_color.rgb = RGBColor(241, 245, 249)
    b_tech.line.color.rgb = RGBColor(226, 232, 240)
    b_tech.line.width = Pt(1)
    ttf = b_tech.text_frame
    ttf.word_wrap = True
    ttf.margin_left = ttf.margin_right = Inches(0.18)
    ttf.margin_top = ttf.margin_bottom = Inches(0.06)

    p_tech = ttf.paragraphs[0]
    p_tech.text = "Technology used (Verified in Codebase):"
    p_tech.font.bold = True
    p_tech.font.size = Pt(9.5)
    p_tech.font.color.rgb = c_navy

    p_tech_items = ttf.add_paragraph()
    p_tech_items.text = "Data / API: Python, FastAPI   |   Analysis: LightGBM, Scikit-learn (Isolation Forest), Rule-based Quality Checks (CUSUM, Step, Range, Spatial Consensus)   |   Storage: SQLite (Local Default), PostgreSQL (Production DB)   |   Dashboard: Next.js 14, React 18, MapLibre GL, Recharts, Tailwind CSS"
    p_tech_items.font.size = Pt(9)
    p_tech_items.font.color.rgb = c_dark

    prs.save("sih26073_technical_approach.pptx")
    print("Successfully generated sih26073_technical_approach.pptx")

if __name__ == "__main__":
    create_pptx()
