"""
scholarships/signals.py
────────────────────────
Django post-save signal for ScholarshipAward.

When transfer_status becomes 'APPROVED', automatically generates a
ScholarshipCertificate for the winning student.
"""
from __future__ import annotations
import logging
from django.db.models.signals import post_save
from django.dispatch import receiver

logger = logging.getLogger(__name__)


def _connect_signals():
    """
    Called from ScholarshipsConfig.ready().
    We define the receiver here so it only registers once.
    """
    from scholarships.models import ScholarshipAward

    @receiver(post_save, sender=ScholarshipAward, dispatch_uid='auto_generate_certificate')
    def generate_certificate_on_approval(sender, instance, created, **kwargs):
        """
        Fire certificate generation whenever a ScholarshipAward is saved
        with transfer_status == 'APPROVED' and no certificate exists yet.
        """
        if instance.transfer_status == 'APPROVED':
            # Avoid circular imports — import lazily
            from scholarships.models import ScholarshipCertificate
            already_has = ScholarshipCertificate.objects.filter(award=instance).exists()
            if not already_has:
                try:
                    from scholarships.certificate_generator import generate_certificate
                    cert = generate_certificate(instance)
                    logger.info(
                        'Certificate auto-generated: %s for student %s',
                        cert.certificate_id, instance.student
                    )
                except Exception as exc:
                    logger.error(
                        'Certificate generation failed for award %s: %s',
                        instance.pk, exc
                    )
