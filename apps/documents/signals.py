"""
Signals for the documents app.

Handles consent-related events and notifications.
"""
import logging

from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import ConsentRecord, DocumentVersion

logger = logging.getLogger(__name__)


@receiver(post_save, sender=DocumentVersion)
def handle_new_document_version(sender, instance, created, **kwargs):
    """
    Handle new document versions.

    If requires_re_consent is True, invalidate previous consents
    and notify affected members.
    """
    if created and instance.requires_re_consent and instance.is_current:
        # Get previous version consents for this document
        previous_consents = ConsentRecord.objects.filter(
            document_version__document=instance.document,
            is_active=True,
        ).exclude(document_version=instance)

        # Mark them as superseded
        count = previous_consents.count()
        if count > 0:
            previous_consents.update(is_active=False)
            logger.info(
                f"Superseded {count} consents for document {instance.document.slug} "
                f"due to new version {instance.version_number}"
            )

            # TODO: Send re-consent notification emails
            # This will be implemented with the notification tasks


@receiver(post_save, sender=ConsentRecord)
def handle_new_consent(sender, instance, created, **kwargs):
    """
    Handle new consent records.

    Updates membership status when required documents are signed.
    """
    if created:
        logger.info(
            f"New consent recorded: {instance.profile} consented to "
            f"{instance.document_version}"
        )
        # The membership status is computed dynamically from consents,
        # so no explicit update needed here
