# Claude Instructions - Nobodies Profiles

Project-specific guidance for Claude Code when working on this codebase.

## Project Overview

This is a Django 5.x membership management system for a Spanish nonprofit. Key domains:
- **accounts**: Custom User model (email-based, Google OAuth)
- **members**: Profile, RoleAssignment, membership status
- **applications**: Application workflow with FSM states
- **documents**: Legal documents synced from git, consent tracking
- **teams**: Working groups and team memberships
- **google_sync**: Google Drive permission provisioning
- **gdpr**: Data export and anonymization requests

## Critical Rules

### 1. Custom User Model
The custom User model in `accounts` MUST exist before any migrations. Never use Django's default `auth.User`. All user references should use `get_user_model()` or `settings.AUTH_USER_MODEL`.

### 2. ConsentRecord Immutability
**NEVER** add update or delete methods to ConsentRecord. This table is append-only for legal compliance. Revocations create separate ConsentRevocation records.

### 3. Membership Status is Computed
`Profile.membership_status` is derived from:
- Active RoleAssignment exists?
- All required ConsentRecords for current DocumentVersions?
- Not past re-consent deadline?

Never set status directly. Implement as a computed property or denormalized with signals.

### 4. Google API Rate Limiting
Always use Celery tasks for Google API calls. Implement exponential backoff. The reconciliation job should spread calls over time, not batch-blast.

### 5. Spanish is Canonical
For legal documents, Spanish (`es`) content is legally binding. Translations are reference-only. UI must always show Spanish as primary with clear disclaimer on translations.

## Code Patterns

### FSM Transitions (django-fsm)
```python
from django_fsm import transition, FSMField

class Application(models.Model):
    status = FSMField(default='SUBMITTED')

    @transition(field=status, source='SUBMITTED', target='UNDER_REVIEW')
    def start_review(self):
        pass

    @transition(field=status, source='UNDER_REVIEW', target='APPROVED')
    def approve(self):
        # Side effects: create Profile, RoleAssignment
        pass
```

### Audit Logging
Use `django-simple-history` on models that need audit trails:
```python
from simple_history.models import HistoricalRecords

class RoleAssignment(models.Model):
    # ... fields ...
    history = HistoricalRecords()
```

### Celery Tasks
```python
from celery import shared_task

@shared_task(bind=True, max_retries=3)
def provision_google_access(self, profile_id):
    try:
        # ... API call ...
    except GoogleAPIError as e:
        self.retry(exc=e, countdown=60 * (2 ** self.request.retries))
```

### GDPR Consent UI Pattern
```html
{# Always show Spanish primary #}
<div class="document-content">
    {{ document_version.spanish_content|safe }}
</div>

{# Translation selector with disclaimer #}
{% if translations %}
<div class="translation-notice">
    This translation is for reference only. The Spanish version is legally binding.
</div>
{% endif %}

{# Explicit unchecked checkbox #}
<label>
    <input type="checkbox" name="consent" required>
    I have read and agree to {{ document.title }} version {{ version.version_number }}.
    I acknowledge that the Spanish version is legally binding.
</label>
```

## Testing Approach

### Model Tests
- Test FSM transitions and their side effects
- Test computed membership status under all conditions
- Test consent record creation captures all required fields

### Integration Tests
- Test full application → approval → document signing → active flow
- Test Google sync with mocked API responses
- Test re-consent campaign triggers status changes

### GDPR Tests
- Verify data export includes all personal data
- Verify anonymization replaces PII but preserves structure
- Verify consent records are never modified

## File Structure

```
nobodies-profiles/
├── config/                    # Django project config
│   ├── settings/
│   │   ├── base.py
│   │   ├── local.py
│   │   └── production.py
│   ├── celery.py
│   ├── urls.py
│   └── wsgi.py
├── apps/
│   ├── accounts/              # Custom User model
│   ├── members/               # Profile, RoleAssignment
│   ├── applications/          # Application workflow
│   ├── documents/             # Legal docs, consent
│   ├── teams/                 # Working groups
│   ├── google_sync/           # Drive API integration
│   └── gdpr/                  # Data export, deletion
├── templates/
│   ├── base.html
│   ├── accounts/
│   ├── members/
│   └── ...
├── static/
├── locale/                    # i18n translations
│   ├── es/
│   ├── en/
│   └── ...
├── docker/
│   ├── Dockerfile
│   └── docker-compose.yml
├── requirements/
│   ├── base.txt
│   ├── local.txt
│   └── production.txt
└── manage.py
```

## Environment

### Local Development
```bash
docker compose up -d db redis    # Start services
python manage.py runserver       # Django dev server
celery -A config worker -l INFO  # In another terminal
```

### Database
PostgreSQL 16 in Docker. Connection via `DATABASE_URL` env var.

### Redis
Redis 7 for Celery broker and Django cache. Connection via `REDIS_URL`.

## Common Tasks

### Adding a New Legal Document Type
1. Add choice to `LegalDocument.document_type`
2. Create migration
3. Add document to `nobodies-collective/legal` repo
4. Sync will create DocumentVersion automatically

### Modifying Membership Status Logic
Status is computed in `Profile.membership_status`. Update the property and add tests for all edge cases.

### Adding Google Resource Access
1. Create GoogleResource in admin
2. Link to Role via RoleGoogleAccess or Team via TeamGoogleAccess
3. Reconciliation task will grant access on next run

## Dependencies

See `requirements/base.txt`. Key packages:
- `django-allauth` - Google OAuth
- `django-fsm` - State machine workflows
- `django-simple-history` - Audit trails
- `celery[redis]` - Background tasks
- `google-api-python-client` - Drive API

## Deployment

Docker Compose with traefik integration. See `docker/docker-compose.yml`.

Labels for traefik:
```yaml
labels:
  - "traefik.enable=true"
  - "traefik.http.routers.profiles.rule=Host(`profiles.nobodies.team`)"
  - "traefik.http.routers.profiles.entrypoints=websecure"
  - "traefik.http.routers.profiles.tls=true"
  - "traefik.http.services.profiles.loadbalancer.server.port=8000"
```

## Internationalization

- Primary languages: Spanish (es), English (en)
- Future: French (fr), German (de), Portuguese (pt)
- All strings use `{% trans %}` in templates, `gettext_lazy()` in Python
- URL prefix pattern: `/es/dashboard/`, `/en/dashboard/`

## Documentation

### For Developers
- `CLAUDE.md` - This file, AI assistant instructions
- `TODO.md` - Outstanding tasks from code review (security, cleanup, simplification)
- `docs/DEVELOPMENT_PLAN.md` - Original development roadmap

### For Administrators
- `docs/ADMIN_GUIDE.md` - Comprehensive guide for system administrators
- `docs/QUICK_REFERENCE.md` - Quick reference card for common tasks
- `docs/GLOSSARY.md` - Plain-language glossary of terms

### In-App Help
All member-facing pages include collapsible help sections explaining:
- Status meanings and next steps
- GDPR rights and data management
- Document signing requirements
- Application process

## Outstanding Work

See `TODO.md` for prioritized list of:
- **HIGH**: Security fixes (XSS, SECRET_KEY)
- **MEDIUM**: Security improvements (OAuth, GDPR IP anonymization, CSP)
- **Code Cleanup**: Deduplication, logging consistency
- **Simplification**: FSM approach, history tracking scope
- **Performance**: QuerySet optimizations
