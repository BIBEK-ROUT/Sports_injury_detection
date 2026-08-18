import io
import json
from datetime import datetime
from typing import List, Optional, Dict, Any

import matplotlib
matplotlib.use('Agg')  # Non-interactive backend
import matplotlib.pyplot as plt
import numpy as np

from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, KeepTogether, PageBreak, HRFlowable
)
from reportlab.pdfgen import canvas


class NumberedCanvas(canvas.Canvas):
    """Two-pass canvas to add running footer with total page count."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, page_count: int):
        self.saveState()
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#64748b"))
        
        # Header banner line
        self.setStrokeColor(colors.HexColor("#e2e8f0"))
        self.setLineWidth(0.5)
        self.line(36, 756, 576, 756)
        
        # Running top header
        self.drawString(36, 762, "SportGuard AI • Biomechanical Risk Assessment Report")
        self.drawRightString(576, 762, datetime.utcnow().strftime("%B %d, %Y"))
        
        # Footer divider line
        self.line(36, 40, 576, 40)
        
        # Running bottom footer
        self.drawString(36, 28, "CONFIDENTIAL — For Clinical & Coaching Use Only • Powered by SportGuard ML Engine")
        self.drawRightString(576, 28, f"Page {self._pageNumber} of {page_count}")
        self.restoreState()


def _generate_page1_charts(analysis) -> io.BytesIO:
    """Generate side-by-side charts for Page 1: Symmetry Bar Chart + Risk Flags."""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(7.2, 2.2), dpi=200)
    fig.patch.set_facecolor('#ffffff')

    # Chart 1: Symmetries
    metrics = ['Overall', 'Knee', 'Hip']
    values = [
        (analysis.avg_overall_symmetry or 0) * 100,
        (analysis.avg_knee_symmetry or 0) * 100,
        (analysis.avg_hip_symmetry or 0) * 100,
    ]
    bar_colors = ['#2563eb' if v >= 85 else '#f59e0b' if v >= 70 else '#ef4444' for v in values]
    
    bars = ax1.barh(metrics, values, color=bar_colors, height=0.55, edgecolor='none', zorder=3)
    ax1.set_xlim(0, 100)
    ax1.set_title('Bilateral Symmetry Index (%)', fontsize=9, fontweight='bold', color='#1e293b', pad=8)
    ax1.grid(axis='x', linestyle='--', alpha=0.4, color='#cbd5e1', zorder=0)
    ax1.tick_params(labelsize=8, colors='#475569')
    ax1.axvline(85, color='#16a34a', linestyle=':', linewidth=1, label='Target (85%)')
    for spine in ax1.spines.values():
        spine.set_visible(False)

    for bar, val in zip(bars, values):
        ax1.text(val + 2, bar.get_y() + bar.get_height()/2, f"{val:.1f}%", 
                 va='center', ha='left', fontsize=8, fontweight='bold', color='#1e293b')

    # Chart 2: Risk Flags Count
    flags = ['Knee Valgus', 'Hyperext', 'Trunk Lean', 'Low Symm', 'Acute Flex']
    counts = [
        analysis.frames_knee_valgus or 0,
        analysis.frames_knee_hyperextension or 0,
        analysis.frames_excessive_trunk_lean or 0,
        analysis.frames_low_symmetry or 0,
        analysis.frames_knee_acute_flexion or 0,
    ]
    flag_colors = ['#ef4444' if c > 5 else '#f59e0b' if c > 0 else '#94a3b8' for c in counts]
    
    bars2 = ax2.bar(flags, counts, color=flag_colors, width=0.55, edgecolor='none', zorder=3)
    ax2.set_title('Risk Flags (Frames Detected)', fontsize=9, fontweight='bold', color='#1e293b', pad=8)
    ax2.grid(axis='y', linestyle='--', alpha=0.4, color='#cbd5e1', zorder=0)
    ax2.tick_params(labelsize=7.5, colors='#475569')
    plt.setp(ax2.get_xticklabels(), rotation=15, ha='right')
    for spine in ax2.spines.values():
        spine.set_visible(False)

    max_c = max(max(counts), 10)
    ax2.set_ylim(0, max_c * 1.25)
    for bar, c in zip(bars2, counts):
        if c > 0:
            ax2.text(bar.get_x() + bar.get_width()/2, c + (max_c * 0.04), str(c),
                     ha='center', va='bottom', fontsize=7.5, fontweight='bold', color='#1e293b')

    plt.tight_layout()
    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=200, bbox_inches='tight', facecolor='#ffffff')
    plt.close(fig)
    buf.seek(0)
    return buf


def _generate_page2_trend_chart(history_records: List[Any]) -> Optional[io.BytesIO]:
    """Generate longitudinal symmetry & risk trend over previous sessions up to this date."""
    if not history_records or len(history_records) < 2:
        return None

    # Sort chronological - keep up to 6 sessions up to current
    records = sorted(history_records, key=lambda x: x.created_at or datetime.min)[-6:]
    
    dates = [r.created_at.strftime("%d %b") if hasattr(r, 'created_at') and r.created_at else f"S{i+1}" for i, r in enumerate(records)]
    symmetries = [(r.avg_overall_symmetry or 0) * 100 for r in records]
    
    fig, ax = plt.subplots(figsize=(7.2, 1.8), dpi=200)
    fig.patch.set_facecolor('#ffffff')
    
    x_indices = list(range(len(dates)))
    ax.plot(x_indices, symmetries, marker='o', color='#2563eb', linewidth=2.2, markersize=6.5, label='Overall Symmetry (%)', zorder=4)
    ax.fill_between(x_indices, symmetries, 40, color='#3b82f6', alpha=0.08, zorder=2)
    
    # Threshold lines
    ax.axhline(85, color='#16a34a', linestyle='--', linewidth=1, alpha=0.7, label='Optimal (85%)')
    ax.axhline(70, color='#ef4444', linestyle='--', linewidth=1, alpha=0.7, label='High Risk (<70%)')
    
    ax.set_ylim(40, 112)
    ax.set_xlim(-0.5, len(dates) - 0.5)
    ax.set_xticks(x_indices)
    ax.set_xticklabels(dates, fontsize=8, color='#475569', fontweight='normal')
    ax.set_title('Longitudinal Bilateral Symmetry Progress (Sessions Up To Current Date)', fontsize=9, fontweight='bold', color='#1e293b', pad=8)
    ax.grid(axis='y', linestyle='--', alpha=0.4, color='#cbd5e1', zorder=0)
    ax.tick_params(labelsize=8, colors='#475569')
    ax.legend(loc='lower left', fontsize=7, frameon=True, facecolor='#f8fafc', edgecolor='#e2e8f0')
    
    for spine in ax.spines.values():
        spine.set_visible(False)
        
    for x, s in zip(x_indices, symmetries):
        # Position badge cleanly above point (or below if near 100%)
        y_offset = 5.0 if s < 96 else -12.0
        ax.annotate(
            f"{s:.0f}%",
            (x, s),
            textcoords="offset points",
            xytext=(0, y_offset),
            ha='center',
            va='center',
            fontsize=8,
            fontweight='bold',
            color='#0f172a',
            bbox=dict(boxstyle='round,pad=0.2', facecolor='#ffffff', edgecolor='#cbd5e1', alpha=0.95, linewidth=0.6)
        )

    plt.tight_layout()
    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=200, bbox_inches='tight', facecolor='#ffffff')
    plt.close(fig)
    buf.seek(0)
    return buf


def generate_athlete_report_pdf(
    analysis: Any,
    athlete_user: Any,
    athlete_profile: Optional[Any] = None,
    history_records: Optional[List[Any]] = None,
) -> io.BytesIO:
    """
    Builds an executive 2-page Clinical & Biomechanical PDF Assessment Report.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        leftMargin=36,
        rightMargin=36,
        topMargin=46,
        bottomMargin=46,
    )

    styles = getSampleStyleSheet()
    
    # Custom Typography Styles
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=16,
        leading=19,
        textColor=colors.HexColor('#0f172a'),
    )
    subtitle_style = ParagraphStyle(
        'DocSubTitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor('#64748b'),
    )
    section_heading = ParagraphStyle(
        'SectionHeading',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=10,
        leading=13,
        textColor=colors.HexColor('#1e40af'),
        spaceBefore=6,
        spaceAfter=4,
    )
    body_bold = ParagraphStyle(
        'BodyBold',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor('#1e293b'),
    )
    body_text = ParagraphStyle(
        'BodyText',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8,
        leading=10.5,
        textColor=colors.HexColor('#334155'),
    )

    story = []

    # ══════════════════════════════════════════════════════════════════
    # PAGE 1: CURRENT SESSION BIOMECHANICS & TELEMETRY
    # ══════════════════════════════════════════════════════════════════

    # Header section with title and session badge
    session_dt = analysis.created_at if hasattr(analysis, 'created_at') and analysis.created_at else datetime.utcnow()
    session_date_str = session_dt.strftime('%d %b %Y, %H:%M') if hasattr(session_dt, 'strftime') else str(session_dt)
    
    header_data = [
        [
            Paragraph("<b>SPORTGUARD BIOMECHANICAL REPORT</b>", title_style),
            Paragraph(f"<b>SESSION ID:</b> #{analysis.session_id[:10]}<br/><b>SESSION DATE:</b> {session_date_str}", subtitle_style)
        ]
    ]
    header_table = Table(header_data, colWidths=[360, 180])
    header_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('ALIGN', (1,0), (1,0), 'RIGHT'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 0),
        ('TOPPADDING', (0,0), (-1,-1), 0),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 8))

    # 1. Athlete Information Box
    name = f"{athlete_user.first_name} {athlete_user.last_name}" if athlete_user else "Unknown Athlete"
    sport = athlete_profile.sport_type if athlete_profile else (analysis.sport_type_used or "General Sports")
    position = athlete_profile.position if athlete_profile and athlete_profile.position else "N/A"
    age = f"{athlete_profile.age} yrs" if athlete_profile and athlete_profile.age else "N/A"
    height = f"{athlete_profile.height_cm} cm" if athlete_profile and athlete_profile.height_cm else "N/A"
    weight = f"{athlete_profile.weight_kg} kg" if athlete_profile and athlete_profile.weight_kg else "N/A"
    training_hrs = f"{athlete_profile.weekly_training_hours} hrs/wk" if athlete_profile and athlete_profile.weekly_training_hours else "N/A"
    dominant_limb = athlete_profile.dominant_limb if athlete_profile and athlete_profile.dominant_limb else "Right"

    athlete_info_data = [
        [
            Paragraph(f"<b>Athlete:</b> {name}", body_text),
            Paragraph(f"<b>Sport / Position:</b> {sport} ({position})", body_text),
            Paragraph(f"<b>Age / Sex:</b> {age} / {athlete_profile.gender if athlete_profile and athlete_profile.gender else 'N/A'}", body_text),
        ],
        [
            Paragraph(f"<b>Height / Weight:</b> {height} / {weight}", body_text),
            Paragraph(f"<b>Dominant Limb:</b> {dominant_limb}", body_text),
            Paragraph(f"<b>Training Load:</b> {training_hrs}", body_text),
        ]
    ]
    athlete_table = Table(athlete_info_data, colWidths=[180, 180, 180])
    athlete_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#f8fafc')),
        ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor('#e2e8f0')),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#f1f5f9')),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
        ('RIGHTPADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(athlete_table)
    story.append(Spacer(1, 6))

    # 2. Risk Classification Banner
    risk_level = (analysis.risk_level or "low").upper()
    confidence = (analysis.xgboost_confidence or 0) * 100
    
    risk_bg = colors.HexColor('#fee2e2') if risk_level in ['HIGH', 'CRITICAL'] else colors.HexColor('#fef3c7') if risk_level == 'MODERATE' else colors.HexColor('#dcfce7')
    risk_txt = colors.HexColor('#991b1b') if risk_level in ['HIGH', 'CRITICAL'] else colors.HexColor('#92400e') if risk_level == 'MODERATE' else colors.HexColor('#166534')
    
    probs_dict = {}
    if analysis.xgboost_probabilities:
        try:
            probs_dict = json.loads(analysis.xgboost_probabilities) if isinstance(analysis.xgboost_probabilities, str) else analysis.xgboost_probabilities
        except:
            probs_dict = {}

    prob_str = " | ".join([f"{k.capitalize()}: {v*100:.1f}%" for k, v in probs_dict.items()]) if probs_dict else "Probabilities calculated"

    risk_data = [
        [
            Paragraph(f"<b>INJURY RISK CLASSIFICATION:</b> <font size='11'><b>{risk_level} RISK</b></font> (Model Confidence: {confidence:.1f}%)", ParagraphStyle('RiskT', parent=body_bold, textColor=risk_txt)),
        ],
        [
            Paragraph(f"<b>Class Probabilities:</b> {prob_str} • <b>Video Analysis:</b> {analysis.duration_seconds or 0:.1f}s ({analysis.frames_analyzed or 0} frames analyzed, {analysis.pose_detection_rate or 0:.1f}% pose detection rate)", body_text),
        ]
    ]
    risk_table = Table(risk_data, colWidths=[540])
    risk_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), risk_bg),
        ('BOX', (0,0), (-1,-1), 1, risk_txt),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ('LEFTPADDING', (0,0), (-1,-1), 8),
        ('RIGHTPADDING', (0,0), (-1,-1), 8),
    ]))
    story.append(risk_table)
    story.append(Spacer(1, 6))

    # 3. Biomechanical Telemetry Table
    story.append(Paragraph("BIOMECHANICAL METRIC MEASUREMENTS & SYMMETRY", section_heading))
    
    def _fmt_deg(val):
        return f"{val:.1f}°" if val is not None else "—"

    telemetry_data = [
        ["Joint / Movement Metric", "Left Side", "Right Side", "Symmetry Index", "Clinical Norm", "Assessment"],
        [
            "Knee Flexion (Average)",
            _fmt_deg(analysis.avg_left_knee_angle),
            _fmt_deg(analysis.avg_right_knee_angle),
            f"{(analysis.avg_knee_symmetry or 0)*100:.1f}%",
            "> 85% Symm",
            "Optimal" if (analysis.avg_knee_symmetry or 0) >= 0.85 else "Asymmetric",
        ],
        [
            "Knee Flexion (Peak/Min)",
            _fmt_deg(analysis.min_left_knee_angle),
            _fmt_deg(analysis.min_right_knee_angle),
            "—",
            "60° - 140°",
            "Monitored",
        ],
        [
            "Hip Angle (Average)",
            _fmt_deg(analysis.avg_left_hip_angle),
            _fmt_deg(analysis.avg_right_hip_angle),
            f"{(analysis.avg_hip_symmetry or 0)*100:.1f}%",
            "> 85% Symm",
            "Optimal" if (analysis.avg_hip_symmetry or 0) >= 0.85 else "Deficit",
        ],
        [
            "Elbow Angle (Average)",
            _fmt_deg(analysis.avg_left_elbow_angle),
            _fmt_deg(analysis.avg_right_elbow_angle),
            "—",
            "—",
            "Normal",
        ],
        [
            "Knee Valgus Angle (FPPA)",
            "—",
            "—",
            _fmt_deg(analysis.avg_knee_valgus_angle),
            "< 15.0°",
            "HIGH RISK" if (analysis.avg_knee_valgus_angle or 0) > 15 else "Normal",
        ],
        [
            "Trunk Lateral Lean",
            "—",
            "—",
            _fmt_deg(analysis.avg_trunk_lean),
            "< 20.0°",
            "Compensatory" if (analysis.avg_trunk_lean or 0) > 20 else "Stable",
        ],
        [
            "Shoulder Rotation Angle",
            "—",
            "—",
            _fmt_deg(analysis.avg_shoulder_rotation),
            "< 35.0°",
            "Normal",
        ],
    ]

    telemetry_table = Table(telemetry_data, colWidths=[150, 75, 75, 80, 80, 80])
    telemetry_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1e293b')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,-1), 7.5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('ALIGN', (1,0), (-1,-1), 'CENTER'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#e2e8f0')),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#f8fafc')]),
    ]))
    story.append(telemetry_table)
    story.append(Spacer(1, 6))

    # 4. Embed Page 1 Visual Charts
    story.append(Paragraph("VISUAL SYMMETRY & RISK FLAG PROFILES", section_heading))
    chart1_buf = _generate_page1_charts(analysis)
    story.append(Image(chart1_buf, width=7.2*inch, height=2.2*inch))

    # ══════════════════════════════════════════════════════════════════
    # PAGE 2: MULTI-SESSION TREND, MEDICAL HISTORY & AI PRESCRIPTION
    # ══════════════════════════════════════════════════════════════════
    story.append(PageBreak())

    # Header for Page 2
    story.append(Paragraph("LONGITUDINAL MONITORING & CORRECTIVE PRESCRIPTION", section_heading))
    story.append(Spacer(1, 2))

    # 1. Multi-session Trend Chart (if available)
    if history_records and len(history_records) >= 2:
        trend_buf = _generate_page2_trend_chart(history_records)
        if trend_buf:
            story.append(Paragraph("<b>1. Multi-Session Bilateral Symmetry Progression</b>", body_bold))
            story.append(Image(trend_buf, width=7.2*inch, height=1.7*inch))
            story.append(Spacer(1, 6))

    # 2. Athlete Medical & Past Injury History Context
    story.append(Paragraph("<b>2. Clinical Medical & Injury History Context</b>", body_bold))
    injury_records = athlete_profile.injury_histories if athlete_profile and athlete_profile.injury_histories else []
    
    if injury_records:
        inj_table_data = [["Injury / Condition", "Affected Body Part", "Injury Date", "Recovery Duration", "Clinical Notes"]]
        for inj in injury_records[:3]:  # Top 3
            clean_inj_name = inj.injury_name.replace("_", " ").title() if inj.injury_name else "—"
            clean_body_part = inj.affected_body_part.replace("_", " ").title() if inj.affected_body_part else "—"
            inj_table_data.append([
                clean_inj_name,
                clean_body_part,
                inj.injury_date.strftime("%b %Y") if hasattr(inj.injury_date, 'strftime') else str(inj.injury_date),
                f"{inj.recovery_duration_weeks} weeks" if inj.recovery_duration_weeks else "N/A",
                inj.notes or "—"
            ])
        inj_table = Table(inj_table_data, colWidths=[120, 100, 70, 90, 160])
        inj_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#f1f5f9')),
            ('TEXTCOLOR', (0,0), (-1,0), colors.HexColor('#334155')),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('FONTSIZE', (0,0), (-1,-1), 7.5),
            ('TOPPADDING', (0,0), (-1,-1), 2.5),
            ('BOTTOMPADDING', (0,0), (-1,-1), 2.5),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#cbd5e1')),
        ]))
        story.append(inj_table)
    else:
        no_inj_box = Table([[Paragraph("<i>No previous musculoskeletal injuries recorded in athlete profile.</i>", body_text)]], colWidths=[540])
        no_inj_box.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#f8fafc')),
            ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor('#e2e8f0')),
            ('PADDING', (0,0), (-1,-1), 4),
        ]))
        story.append(no_inj_box)

    story.append(Spacer(1, 8))

    # 3. AI Corrective Prescription (Gemini Generated)
    story.append(Paragraph("<b>3. AI-Generated Corrective & Rehabilitation Prescription</b>", body_bold))
    
    ai_recs = {}
    if analysis.ai_recommendations:
        try:
            ai_recs = json.loads(analysis.ai_recommendations) if isinstance(analysis.ai_recommendations, str) else analysis.ai_recommendations
        except:
            ai_recs = {}

    exercises = ai_recs.get("exercise_recommendations", ["Targeted single-leg stability exercises (3 sets x 10 reps)", "Gluteus medius strengthening with resistance bands"])
    mobility = ai_recs.get("mobility_suggestions", ["Dynamic hamstring and adductor stretching post-session", "Ankle dorsiflexion mobility drills"])
    recovery = ai_recs.get("recovery_planning", ["Ensure 48h active recovery between high-intensity jumping sessions", "Implement contrast hydrotherapy or icing protocol for active inflammation"])

    ex_text = "<br/>• ".join(exercises)
    mob_text = "<br/>• ".join(mobility)
    rec_text = "<br/>• ".join(recovery)

    rec_data = [
        [
            Paragraph("<b>Targeted Corrective Drills</b>", ParagraphStyle('RecH1', parent=body_bold, textColor=colors.HexColor('#1d4ed8'))),
            Paragraph(f"• {ex_text}", body_text),
        ],
        [
            Paragraph("<b>Mobility & Flexibility Routine</b>", ParagraphStyle('RecH2', parent=body_bold, textColor=colors.HexColor('#047857'))),
            Paragraph(f"• {mob_text}", body_text),
        ],
        [
            Paragraph("<b>Recovery & Load Protocol</b>", ParagraphStyle('RecH3', parent=body_bold, textColor=colors.HexColor('#7c3aed'))),
            Paragraph(f"• {rec_text}", body_text),
        ],
    ]

    rec_table = Table(rec_data, colWidths=[140, 400])
    rec_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (0,-1), colors.HexColor('#f8fafc')),
        ('BACKGROUND', (1,0), (1,-1), colors.white),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#e2e8f0')),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
        ('RIGHTPADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(rec_table)
    story.append(Spacer(1, 10))

    # 4. Clinical Verification & Sign-off Box
    disclaimer_data = [
        [
            Paragraph(
                "<b>CLINICAL NOTICE & DISCLAIMER:</b><br/>"
                "This assessment report is generated via computer vision pose estimation and machine learning predictive modeling. "
                "It is designed to assist coaches and physiotherapists in identifying movement asymmetries and injury risk factors. "
                "This report does not constitute a diagnostic medical prescription. Always consult a licensed medical professional for formal clinical evaluation.",
                ParagraphStyle('Disc', parent=styles['Normal'], fontSize=6.8, leading=8.5, textColor=colors.HexColor('#64748b'))
            )
        ]
    ]
    disc_table = Table(disclaimer_data, colWidths=[540])
    disc_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#f8fafc')),
        ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor('#cbd5e1')),
        ('PADDING', (0,0), (-1,-1), 5),
    ]))
    story.append(disc_table)

    # Build the document with two-pass canvas for footer
    doc.build(story, canvasmaker=NumberedCanvas)
    buffer.seek(0)
    return buffer
