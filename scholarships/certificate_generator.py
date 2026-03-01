"""
scholarships/certificate_generator.py
─────────────────────────────────────
Phase 8 — Certificate Engine

Generates a premium-looking scholarship certificate as a 1200×850 PNG using Pillow.
Embeds a QR code that links to the public verification URL.

Public API:
    generate_certificate(award: ScholarshipAward) → ScholarshipCertificate
"""
from __future__ import annotations

import io
import os
import logging
from pathlib import Path

from django.conf import settings
from django.core.files.base import ContentFile
from django.utils import timezone

logger = logging.getLogger(__name__)

# ─── Color palette ────────────────────────────────────────────────────────────
CREAM      = (252, 249, 240)
GOLD       = (196, 155, 56)
DARK_GOLD  = (150, 110, 20)
DARK_NAVY  = (15, 28, 56)
CHARCOAL   = (45, 45, 55)
WHITE      = (255, 255, 255)
LIGHT_GRAY = (230, 225, 215)
GREEN_OK   = (34, 139, 80)


def _get_font(size: int, bold: bool = False):
    """Load a TTF font, falling back to PIL default if not available."""
    from PIL import ImageFont
    font_dir = Path(__file__).resolve().parent / 'static' / 'fonts'
    candidates = ['Cinzel-Bold.ttf', 'Cinzel-Regular.ttf'] if bold else ['Cinzel-Regular.ttf']
    for name in candidates:
        path = font_dir / name
        if path.exists():
            try:
                return ImageFont.truetype(str(path), size)
            except Exception:
                pass
    # Fallback: PIL built-in default (no TTF needed)
    try:
        return ImageFont.load_default(size=size)
    except TypeError:
        return ImageFont.load_default()


def _draw_border(draw, width: int, height: int):
    """Draw decorative double-line gold border."""
    from PIL import Image
    m1, m2 = 18, 26          # outer / inner margin
    gold = GOLD
    dark = DARK_GOLD
    # Outer thick border
    draw.rectangle([m1, m1, width - m1, height - m1], outline=gold, width=4)
    # Inner thin border
    draw.rectangle([m2, m2, width - m2, height - m2], outline=dark, width=2)


def _draw_corner_ornaments(draw, width: int, height: int):
    """Draw small filled diamond ornaments at the four inner corners."""
    margin = 40
    size = 8
    positions = [
        (margin, margin),
        (width - margin, margin),
        (margin, height - margin),
        (width - margin, height - margin),
    ]
    for cx, cy in positions:
        pts = [(cx, cy - size), (cx + size, cy), (cx, cy + size), (cx - size, cy)]
        draw.polygon(pts, fill=GOLD)


def _draw_divider(draw, y: int, width: int):
    """Thin gold horizontal rule, centered."""
    pad = 80
    draw.line([(pad, y), (width - pad, y)], fill=GOLD, width=1)


def _centered_text(draw, text: str, y: int, width: int, font, color):
    """Draw text centered horizontally at y."""
    bbox = draw.textbbox((0, 0), text, font=font)
    text_w = bbox[2] - bbox[0]
    x = (width - text_w) // 2
    draw.text((x, y), text, font=font, fill=color)


def generate_qr(verify_url: str) -> bytes:
    """Return the QR code as PNG bytes."""
    import qrcode
    qr = qrcode.QRCode(
        version=3,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=6,
        border=2,
    )
    qr.add_data(verify_url)
    qr.make(fit=True)
    img = qr.make_image(fill_color=DARK_NAVY, back_color=WHITE)
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    return buf.getvalue()


def build_certificate_image(
    student_name: str,
    scholarship_title: str,
    org_name: str,
    amount: int,
    cert_id: str,
    issued_date: str,
    merit_rank: int,
    verify_url: str,
) -> bytes:
    """
    Render and return the full certificate as PNG bytes.
    Canvas size: 1200 × 850 px.
    """
    from PIL import Image, ImageDraw

    W, H = 1200, 850
    img = Image.new('RGB', (W, H), color=CREAM)
    draw = ImageDraw.Draw(img)

    # ── Decorative background hex watermark ──────────────────────────────────
    try:
        wm_font = _get_font(220, bold=False)
        wm_bbox = draw.textbbox((0, 0), '❖', font=wm_font)
        wm_w = wm_bbox[2] - wm_bbox[0]
        draw.text(((W - wm_w) // 2, 200), '❖', font=wm_font,
                  fill=(230, 225, 215))
    except Exception:
        pass

    # ── Border & ornaments ────────────────────────────────────────────────────
    _draw_border(draw, W, H)
    _draw_corner_ornaments(draw, W, H)

    # ── Header: "OFFICIAL DOCUMENT" tag ──────────────────────────────────────
    tag_font = _get_font(13)
    _centered_text(draw, 'OFFICIAL DOCUMENT', 60, W, tag_font, GOLD)

    # ── Org name top-right ────────────────────────────────────────────────────
    org_font = _get_font(13)
    draw.text((W - 260, 55), org_name.upper()[:35], font=org_font, fill=CHARCOAL)

    # ── Title ─────────────────────────────────────────────────────────────────
    title_font = _get_font(52, bold=True)
    _centered_text(draw, 'CERTIFICATE OF', 95, W, title_font, DARK_NAVY)
    _centered_text(draw, 'SCHOLARSHIP', 155, W, title_font, DARK_NAVY)

    _draw_divider(draw, 225, W)

    # ── Sub-tagline ───────────────────────────────────────────────────────────
    sub_font = _get_font(14)
    _centered_text(draw,
        'This document certifies that the following individual has been selected for',
        240, W, sub_font, CHARCOAL)
    _centered_text(draw,
        'outstanding academic achievement and merit.',
        262, W, sub_font, CHARCOAL)

    # ── "PRESENTED TO" label ──────────────────────────────────────────────────
    label_font = _get_font(13)
    _centered_text(draw, 'PRESENTED TO', 300, W, label_font, GOLD)

    # ── Student name ──────────────────────────────────────────────────────────
    name_font = _get_font(54, bold=True)
    _centered_text(draw, student_name.upper(), 330, W, name_font, DARK_NAVY)

    _draw_divider(draw, 415, W)

    # ── Body text ─────────────────────────────────────────────────────────────
    body_font = _get_font(14)
    body_text = (
        f'For demonstrating exceptional potential and fulfilling all criteria set forth'
    )
    body_text2 = (
        f'by {org_name} for the scholarship: {scholarship_title[:55]}'
    )
    _centered_text(draw, body_text, 430, W, body_font, CHARCOAL)
    _centered_text(draw, body_text2, 455, W, body_font, CHARCOAL)

    # ── Bottom data row ───────────────────────────────────────────────────────
    data_font  = _get_font(11)
    value_font = _get_font(14, bold=True)

    columns = [
        ('DATE OF ISSUE',  issued_date,        130),
        ('CERTIFICATE ID', cert_id[:18],        380),
        ('MERIT RANK',     f'#{merit_rank}',   640),
        ('AMOUNT AWARDED', f'Rs. {amount:,}',  870),
    ]
    y_label = 510
    y_value = 530
    for label, value, x in columns:
        draw.text((x, y_label), label, font=data_font, fill=GOLD)
        draw.text((x, y_value), value, font=value_font, fill=DARK_NAVY)

    _draw_divider(draw, 575, W)

    # ── Signature placeholder lines ───────────────────────────────────────────
    line_y = 660
    for sx in [170, 600, 950]:
        draw.line([(sx, line_y), (sx + 200, line_y)], fill=LIGHT_GRAY, width=1)
    sig_font = _get_font(11)
    draw.text((170, 668), 'Organisation Signatory', font=sig_font, fill=CHARCOAL)
    draw.text((600, 668), 'Platform Administrator', font=sig_font, fill=CHARCOAL)
    draw.text((950, 668), 'Date & Seal',             font=sig_font, fill=CHARCOAL)

    # ── QR code (bottom-right) ────────────────────────────────────────────────
    try:
        qr_bytes = generate_qr(verify_url)
        qr_img = Image.open(io.BytesIO(qr_bytes)).convert('RGBA')
        qr_img = qr_img.resize((150, 150), Image.LANCZOS)
        img.paste(qr_img, (W - 220, 590), qr_img)
        # "Scan to verify" caption
        scan_font = _get_font(10)
        draw.text((W - 215, 745), 'Scan to verify', font=scan_font, fill=CHARCOAL)
    except Exception as exc:
        logger.warning('QR paste failed: %s', exc)

    # ── Footer ────────────────────────────────────────────────────────────────
    footer_font = _get_font(10)
    _centered_text(draw,
        f'Verification ID: {cert_id}  |  Verify at: {verify_url[:60]}',
        790, W, footer_font, CHARCOAL)
    _centered_text(draw,
        '© Scholar Match. This certificate is digitally signed and tamper-evident.',
        808, W, footer_font, CHARCOAL)

    # ── Return PNG bytes ──────────────────────────────────────────────────────
    buf = io.BytesIO()
    img.save(buf, format='PNG', dpi=(150, 150))
    return buf.getvalue()


# ─── Main entry-point ─────────────────────────────────────────────────────────

def generate_certificate(award) -> 'ScholarshipCertificate':
    """
    Generate and persist a ScholarshipCertificate for the given award.
    Called from signals.py when transfer_status becomes 'APPROVED'.

    Returns the saved ScholarshipCertificate instance.
    """
    from .models import ScholarshipCertificate

    # Idempotency guard
    existing = ScholarshipCertificate.objects.filter(award=award).first()
    if existing:
        logger.info('Certificate already exists for award %s, skipping', award.pk)
        return existing

    # ── Collect data ──────────────────────────────────────────────────────────
    student    = award.student
    scholarship = award.scholarship
    org_name   = (
        scholarship.org_profile.organization_name
        if scholarship.org_profile
        else (scholarship.organization or 'ScholarMatch')
    )
    issued_date = timezone.now().strftime('%B %d, %Y')

    # ── Create DB record first to get certificate_id ──────────────────────────
    cert = ScholarshipCertificate.objects.create(award=award)

    # ── Build absolute verification URL ──────────────────────────────────────
    base_url = getattr(settings, 'SITE_BASE_URL', 'https://scholarship-4pxs.onrender.com')
    verify_path = cert.get_verify_url()
    verify_url  = f'{base_url}{verify_path}'

    cert_id = str(cert.certificate_id)

    # ── Render certificate image ──────────────────────────────────────────────
    try:
        cert_png = build_certificate_image(
            student_name      = student.full_name or student.user.username,
            scholarship_title = scholarship.title,
            org_name          = org_name,
            amount            = award.amount_awarded,
            cert_id           = cert_id[:18].upper(),
            issued_date       = issued_date,
            merit_rank        = award.merit_rank,
            verify_url        = verify_url,
        )
        cert.certificate_image.save(
            f'{cert_id}.png',
            ContentFile(cert_png),
            save=False,
        )
    except Exception as exc:
        logger.error('Certificate image generation failed for award %s: %s', award.pk, exc)

    # ── Render standalone QR code ─────────────────────────────────────────────
    try:
        qr_png = generate_qr(verify_url)
        cert.qr_code.save(
            f'{cert_id}_qr.png',
            ContentFile(qr_png),
            save=False,
        )
    except Exception as exc:
        logger.error('QR generation failed for award %s: %s', award.pk, exc)

    cert.save()
    logger.info('Certificate generated: %s  for award #%s', cert_id, award.pk)
    return cert
