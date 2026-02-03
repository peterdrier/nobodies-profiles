"""
GDPR services for data export and anonymization.

DataExportService: Generates ZIP file with all user personal data
AnonymizationService: Anonymizes user data while preserving structure
"""
import hashlib
import io
import json
import zipfile
from datetime import datetime

from django.conf import settings
from django.db import transaction


class DataExportService:
    """
    Service for exporting all personal data for a profile.

    Generates a ZIP file containing:
    - profile.json: Profile data
    - account.json: User account data
    - role_assignments.json: Role history
    - consent_records.json: Consent history
    - team_memberships.json: Team membership history
    - applications.json: Application history
    - google_access_logs.json: Google permission logs
    - audit_logs.json: Audit log entries
    - change_history.json: All model change history
    - README.txt: Explanation of contents
    """

    def __init__(self, profile):
        self.profile = profile
        self.user = profile.user

    def generate_export(self) -> io.BytesIO:
        """Generate ZIP file with all personal data."""
        buffer = io.BytesIO()

        with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
            # Profile data
            zf.writestr('profile.json', self._export_profile())

            # Account data
            zf.writestr('account.json', self._export_account())

            # Role assignments
            zf.writestr('role_assignments.json', self._export_role_assignments())

            # Consent records
            zf.writestr('consent_records.json', self._export_consent_records())

            # Team memberships
            zf.writestr('team_memberships.json', self._export_team_memberships())

            # Applications
            zf.writestr('applications.json', self._export_applications())

            # Google access logs
            zf.writestr('google_access_logs.json', self._export_google_access_logs())

            # Audit logs
            zf.writestr('audit_logs.json', self._export_audit_logs())

            # Change history
            zf.writestr('change_history.json', self._export_change_history())

            # README
            zf.writestr('README.txt', self._generate_readme())

        buffer.seek(0)
        return buffer

    def _export_profile(self) -> str:
        """Export profile data as JSON."""
        data = {
            'id': self.profile.id,
            'legal_name': self.profile.legal_name,
            'country_of_residence': self.profile.country_of_residence,
            'membership_status': self.profile.membership_status,
            'current_role': self.profile.current_role,
            'created_at': self.profile.created_at.isoformat(),
            'updated_at': self.profile.updated_at.isoformat(),
        }
        return json.dumps(data, indent=2, ensure_ascii=False)

    def _export_account(self) -> str:
        """Export user account data as JSON."""
        data = {
            'id': self.user.id,
            'email': self.user.email,
            'display_name': self.user.display_name,
            'preferred_language': self.user.preferred_language,
            'date_joined': self.user.date_joined.isoformat(),
            'last_login': self.user.last_login.isoformat() if self.user.last_login else None,
            'is_active': self.user.is_active,
        }
        return json.dumps(data, indent=2, ensure_ascii=False)

    def _export_role_assignments(self) -> str:
        """Export role assignment history as JSON."""
        assignments = []
        for ra in self.profile.role_assignments.all():
            assignments.append({
                'id': ra.id,
                'role': ra.role,
                'start_date': ra.start_date.isoformat(),
                'end_date': ra.end_date.isoformat(),
                'is_active': ra.is_active,
                'notes': ra.notes,
                'created_at': ra.created_at.isoformat(),
            })
        return json.dumps(assignments, indent=2, ensure_ascii=False)

    def _export_consent_records(self) -> str:
        """Export consent records as JSON."""
        from apps.documents.models import ConsentRecord

        records = []
        for cr in ConsentRecord.objects.filter(profile=self.profile).select_related(
            'document_version__document'
        ):
            records.append({
                'id': cr.id,
                'document': cr.document_version.document.title,
                'version': cr.document_version.version_number,
                'consented_at': cr.consented_at.isoformat(),
                'language_viewed': cr.language_viewed,
                'is_active': cr.is_active,
                'ip_address': cr.ip_address,
            })
        return json.dumps(records, indent=2, ensure_ascii=False)

    def _export_team_memberships(self) -> str:
        """Export team membership history as JSON."""
        memberships = []
        for tm in self.profile.team_memberships.all().select_related('team'):
            memberships.append({
                'id': tm.id,
                'team': tm.team.name,
                'role_in_team': tm.role_in_team,
                'is_active': tm.is_active,
                'joined_at': tm.joined_at.isoformat(),
                'left_at': tm.left_at.isoformat() if tm.left_at else None,
            })
        return json.dumps(memberships, indent=2, ensure_ascii=False)

    def _export_applications(self) -> str:
        """Export application history as JSON."""
        from apps.applications.models import Application

        applications = []
        for app in Application.objects.filter(user=self.user):
            applications.append({
                'id': app.id,
                'status': app.status,
                'role_requested': app.role_requested,
                'legal_name': app.legal_name,
                'preferred_name': app.preferred_name,
                'country_of_residence': app.country_of_residence,
                'how_heard': app.how_heard,
                'motivation': app.motivation,
                'attended_before': app.attended_before,
                'attended_years': app.attended_years,
                'skills': app.skills,
                'submitted_at': app.submitted_at.isoformat(),
                'reviewed_at': app.reviewed_at.isoformat() if app.reviewed_at else None,
                'review_notes': app.review_notes,
            })
        return json.dumps(applications, indent=2, ensure_ascii=False)

    def _export_google_access_logs(self) -> str:
        """Export Google access permission logs as JSON."""
        from apps.google_access.models import GooglePermissionLog

        logs = []
        for log in GooglePermissionLog.objects.filter(profile=self.profile).select_related('resource'):
            logs.append({
                'id': log.id,
                'resource': log.resource.name if log.resource else None,
                'operation': log.operation,
                'permission_role': log.permission_role,
                'status': log.status,
                'triggered_by': log.triggered_by,
                'created_at': log.created_at.isoformat(),
                'completed_at': log.completed_at.isoformat() if log.completed_at else None,
            })
        return json.dumps(logs, indent=2, ensure_ascii=False)

    def _export_audit_logs(self) -> str:
        """Export audit log entries as JSON."""
        from apps.gdpr.models import AuditLog

        logs = []
        for log in AuditLog.objects.filter(profile=self.profile):
            logs.append({
                'id': log.id,
                'category': log.category,
                'action': log.action,
                'description': log.description,
                'ip_address': log.ip_address,
                'timestamp': log.timestamp.isoformat(),
            })
        return json.dumps(logs, indent=2, ensure_ascii=False)

    def _export_change_history(self) -> str:
        """Export model change history from simple_history as JSON."""
        history = []

        # Profile history
        for h in self.profile.history.all():
            history.append({
                'model': 'Profile',
                'history_date': h.history_date.isoformat(),
                'history_type': h.get_history_type_display(),
                'history_user': h.history_user.email if h.history_user else None,
                'legal_name': h.legal_name,
                'country_of_residence': h.country_of_residence,
            })

        # Role assignment history
        for ra in self.profile.role_assignments.all():
            for h in ra.history.all():
                history.append({
                    'model': 'RoleAssignment',
                    'history_date': h.history_date.isoformat(),
                    'history_type': h.get_history_type_display(),
                    'history_user': h.history_user.email if h.history_user else None,
                    'role': h.role,
                    'start_date': h.start_date.isoformat() if h.start_date else None,
                    'end_date': h.end_date.isoformat() if h.end_date else None,
                    'is_active': h.is_active,
                })

        # Team membership history
        for tm in self.profile.team_memberships.all():
            for h in tm.history.all():
                history.append({
                    'model': 'TeamMembership',
                    'history_date': h.history_date.isoformat(),
                    'history_type': h.get_history_type_display(),
                    'history_user': h.history_user.email if h.history_user else None,
                    'role_in_team': h.role_in_team,
                    'is_active': h.is_active,
                })

        return json.dumps(history, indent=2, ensure_ascii=False)

    def _generate_readme(self) -> str:
        """Generate README explaining the export contents."""
        return f"""GDPR Personal Data Export
========================

Export generated: {datetime.now().isoformat()}
Profile: {self.profile.legal_name}
Email: {self.user.email}

This ZIP file contains all personal data associated with your account
at Nobodies Profiles in accordance with GDPR Article 15.

Contents:
---------
- profile.json: Your profile information
- account.json: Your user account details
- role_assignments.json: History of role assignments
- consent_records.json: History of document consents
- team_memberships.json: History of team memberships
- applications.json: Membership application history
- google_access_logs.json: Google Drive access permission logs
- audit_logs.json: System audit log entries
- change_history.json: Complete change history for all your data

Data Retention:
---------------
This export file will expire {settings.GDPR_EXPORT_EXPIRY_DAYS} days after generation.

Questions:
----------
For questions about this data export, please contact the Board at:
board@nobodies.team

---
Generated by Nobodies Profiles
"""


class AnonymizationService:
    """
    Service for anonymizing user data while preserving structure.

    Follows GDPR Article 17 (Right to Erasure) while maintaining
    data integrity for audit and legal compliance purposes.
    """

    def __init__(self, profile):
        self.profile = profile
        self.user = profile.user
        self.hash = self._generate_hash()
        self.log = {}

    def _generate_hash(self) -> str:
        """Generate unique hash for anonymization."""
        data = f"{self.profile.id}|{self.user.email}|{settings.SECRET_KEY}"
        return hashlib.sha256(data.encode()).hexdigest()[:12]

    @transaction.atomic
    def anonymize(self) -> dict:
        """
        Anonymize all personal data for this profile.

        Returns a log of what was anonymized.
        """
        self._anonymize_user()
        self._anonymize_profile()
        self._anonymize_applications()
        self._anonymize_role_assignments()
        self._anonymize_team_memberships()
        self._anonymize_consent_records()
        self._anonymize_profile_tags()

        return self.log

    def _anonymize_user(self):
        """Anonymize User model."""
        original_email = self.user.email

        self.user.email = f"deleted_{self.hash}@deleted.nobodies.team"
        self.user.display_name = f"Deleted User #{self.hash}"
        self.user.is_active = False
        self.user.set_unusable_password()
        self.user.save()

        self.log['user'] = {
            'email': {'old': original_email, 'new': self.user.email},
            'display_name': {'new': self.user.display_name},
            'is_active': False,
        }

    def _anonymize_profile(self):
        """Anonymize Profile model."""
        original_name = self.profile.legal_name
        original_country = self.profile.country_of_residence

        self.profile.legal_name = f"Deleted User #{self.hash}"
        self.profile.country_of_residence = 'XX'
        self.profile.save()

        self.log['profile'] = {
            'legal_name': {'old': original_name, 'new': self.profile.legal_name},
            'country_of_residence': {'old': original_country, 'new': 'XX'},
        }

    def _anonymize_applications(self):
        """Anonymize Application models."""
        from apps.applications.models import Application

        applications = Application.objects.filter(user=self.user)
        count = applications.count()

        for app in applications:
            app.legal_name = '[REDACTED]'
            app.preferred_name = ''
            app.motivation = '[REDACTED]'
            app.skills = '[REDACTED]'
            app.how_heard = '[REDACTED]'
            app.save()

        self.log['applications'] = {
            'count': count,
            'fields_redacted': ['legal_name', 'preferred_name', 'motivation', 'skills', 'how_heard'],
        }

    def _anonymize_role_assignments(self):
        """Deactivate role assignments but preserve structure."""
        count = self.profile.role_assignments.filter(is_active=True).update(
            is_active=False,
            notes='[Anonymized per GDPR request]',
        )

        self.log['role_assignments'] = {
            'deactivated': count,
        }

    def _anonymize_team_memberships(self):
        """Deactivate team memberships but preserve structure."""
        from django.utils import timezone

        count = self.profile.team_memberships.filter(is_active=True).update(
            is_active=False,
            left_at=timezone.now(),
        )

        self.log['team_memberships'] = {
            'deactivated': count,
        }

    def _anonymize_consent_records(self):
        """
        Mark consent records as inactive.

        IMPORTANT: Never delete ConsentRecords per CLAUDE.md rules.
        We only mark them as inactive.
        """
        from apps.documents.models import ConsentRecord

        count = ConsentRecord.objects.filter(
            profile=self.profile,
            is_active=True,
        ).update(is_active=False)

        self.log['consent_records'] = {
            'marked_inactive': count,
            'note': 'Records preserved for legal compliance',
        }

    def _anonymize_profile_tags(self):
        """Remove profile tags."""
        from apps.members.models import ProfileTag

        count, _ = ProfileTag.objects.filter(profile=self.profile).delete()

        self.log['profile_tags'] = {
            'deleted': count,
        }
