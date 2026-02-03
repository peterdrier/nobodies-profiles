# TODO - Nobodies Profiles

Outstanding tasks identified during code review. Prioritized by impact and urgency.

---

## HIGH Priority (Security)

### Fix XSS vulnerability in document content rendering
**File:** `templates/documents/document_detail.html:42`

The template uses Django's `|safe` filter on document content, which could allow XSS attacks if document content contains malicious scripts.

**Solution:** Sanitize HTML with `bleach` or `nh3` library before rendering, or switch to Markdown rendering with a safe renderer.

---

### Remove SECRET_KEY fallback value
**File:** `config/settings/base.py:16`

The SECRET_KEY has a hardcoded fallback value. In production, this is a critical security risk.

**Solution:** Remove the fallback and raise `ImproperlyConfigured` if `DJANGO_SECRET_KEY` environment variable is not set.

```python
SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY')
if not SECRET_KEY:
    raise ImproperlyConfigured("DJANGO_SECRET_KEY environment variable is required")
```

---

## MEDIUM Priority (Security)

### Restrict OAuth auto-signup
**File:** `config/settings/base.py` (allauth settings)

`SOCIALACCOUNT_AUTO_SIGNUP=True` allows any Google account to create an account. This may not be desired.

**Solution:** Either:
1. Add domain whitelist (e.g., only `@nobodies.team` emails)
2. Disable auto-signup and require admin approval
3. Keep as-is if open registration is intended

---

### Anonymize IP addresses in GDPR deletion
**File:** `apps/gdpr/services.py`

The `AnonymizationService` doesn't anonymize IP addresses stored in `ConsentRecord` and `AuditLog` tables.

**Solution:** Add IP address anonymization (e.g., replace with `0.0.0.0`) to the deletion process for full GDPR compliance.

---

### Store Google credentials as file instead of env var
**File:** `config/settings/base.py`

`GOOGLE_SERVICE_ACCOUNT_JSON` is stored as an environment variable. Large JSON blobs in env vars can be problematic.

**Solution:** Mount the credentials file as a Docker secret and read from file path instead.

---

### Add CSP header to production settings
**File:** `config/settings/production.py`

Missing Content-Security-Policy header to prevent inline script execution and other XSS vectors.

**Solution:** Add django-csp or manually configure CSP headers in production settings.

---

## Code Cleanup

### Extract get_client_ip() to shared utility
**Files:**
- `apps/applications/views.py`
- `apps/documents/views.py`
- `apps/gdpr/models.py`

The `get_client_ip()` function is duplicated across multiple files.

**Solution:** Extract to `config/utils.py` and import from there.

---

### Add consistent logging across all apps
**Files:** `apps/members/`, `apps/accounts/`

The `members` and `accounts` apps lack structured logging. Other apps (documents, applications, google_access) have proper logging.

**Solution:** Add logger initialization and usage for critical operations to maintain consistency.

---

## Simplification

### Simplify dual FSM implementation in Application model
**File:** `apps/applications/models.py`

The Application model has both:
1. A CharField `status`
2. A viewflow `State` object

This is redundant and confusing.

**Solution:** Choose one approach:
- Commit fully to viewflow FSM (recommended - it's already integrated)
- Or use simple CharField with custom transition methods

The current setup works but creates unnecessary complexity.

---

### Reduce django-simple-history to essential models
**Files:** Multiple model files

Currently 13+ models have `HistoricalRecords`. Most don't need full audit history.

**Keep history on:**
- `User` - account changes
- `Profile` - membership data
- `RoleAssignment` - role changes
- `Application` - application workflow
- `ConsentRecord` - legal compliance
- `DataDeletionRequest` - GDPR compliance

**Remove from:**
- `Team`, `TeamMembership`
- `CommunityTag`, `ProfileTag`
- `GoogleResource`, `RoleGoogleAccess`, `TeamGoogleAccess`
- `LegalDocument`, `DocumentVersion`

---

### Remove unused dependencies
**File:** `requirements/base.txt`

The following packages appear unused:
- `django-filter` - no filter backends configured
- `djangorestframework` - no API endpoints defined

**Solution:** Remove if not needed, or add a comment explaining future plans.

---

## Performance

### Add QuerySet optimizations throughout views
**Files:** `apps/members/views.py`, `apps/gdpr/views.py`, `apps/documents/views.py`

Several views have N+1 query problems due to missing `select_related()` and `prefetch_related()` calls.

**Solution:** Audit views and add appropriate query optimizations. Example:
```python
# Before
profiles = Profile.objects.all()

# After
profiles = Profile.objects.select_related('user').prefetch_related('profile_tags__tag')
```

---

## Notes

- Tasks are ordered by priority within each section
- Security issues should be addressed before production deployment
- Code cleanup and simplification can be done incrementally
- Performance optimizations can be measured with django-debug-toolbar

*Last updated: 2026-02-03*
