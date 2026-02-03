# Nobodies Profiles - Technical Architecture

## Overview

A membership management system for Asociación Nobodies Collective, handling:
- Membership applications and approval workflows
- Legal document consent tracking (GDPR-compliant)
- Google Drive access provisioning
- Team/working group organization

**Production URL**: `profiles.nobodies.team`

---

## Tech Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| Backend | Django 5.x | Admin views, member portal, API |
| Database | PostgreSQL 16 | Primary data store with audit logging |
| Cache/Broker | Redis 7 | Celery broker + Django cache |
| Task Queue | Celery + celery-beat | Async jobs, scheduled tasks |
| Auth | django-allauth | Google OAuth (sole auth method) |
| API | Django REST Framework | SSO endpoint, future integrations |
| Frontend | Django templates + htmx | Server-rendered with interactive elements |
| Google | google-api-python-client | Drive API via service account |
| Deployment | Docker Compose | web, db, redis, celery-worker, celery-beat |

### Python Dependencies

```
django>=5.0
django-allauth[socialaccount]
django-simple-history          # Audit trail on models
django-fsm                     # State machine workflows
django-filter                  # Admin filtering
djangorestframework
celery[redis]
google-api-python-client
google-auth
django-import-export           # CSV/Excel export
psycopg[binary]                # PostgreSQL adapter
gunicorn
whitenoise                     # Static files
httpx                          # For git sync
```

---

## Docker Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Docker Compose                          │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌──────────────┐   │
│  │   web   │  │   db    │  │  redis  │  │celery-worker │   │
│  │ Django  │  │Postgres │  │ Redis 7 │  │    Celery    │   │
│  │ :8000   │  │  :5432  │  │  :6379  │  │              │   │
│  └────┬────┘  └─────────┘  └─────────┘  └──────────────┘   │
│       │                                                     │
│  ┌────┴────┐                            ┌──────────────┐   │
│  │ volumes │                            │ celery-beat  │   │
│  │ static  │                            │  Scheduler   │   │
│  │ media   │                            └──────────────┘   │
│  └─────────┘                                               │
├─────────────────────────────────────────────────────────────┤
│                    Network: nobodies                        │
│                    External: proxy (traefik)                │
└─────────────────────────────────────────────────────────────┘
```

### Container Details

| Service | Image | Volumes | Notes |
|---------|-------|---------|-------|
| web | Custom Dockerfile | static, media | gunicorn + whitenoise |
| db | postgres:16-alpine | pgdata | Persistent |
| redis | redis:7-alpine | - | Ephemeral OK |
| celery-worker | Same as web | - | `celery -A config worker` |
| celery-beat | Same as web | beat-schedule | `celery -A config beat` |

### Network Strategy

- **Internal network** (`nobodies`): db, redis, celery communicate internally
- **External network** (`proxy`): web connects to traefik for routing
- **No exposed ports**: All access via traefik reverse proxy

---

## Data Model

### Entity Relationship

```
User (auth)
  │
  └──→ Profile (membership data)
         │
         ├──→ RoleAssignment[] (COLABORADOR, ASOCIADO, BOARD_MEMBER)
         │
         ├──→ ConsentRecord[] ──→ DocumentVersion ──→ LegalDocument
         │
         ├──→ TeamMembership[] ──→ Team
         │
         └──→ Application (one per user, tracks approval)

LegalDocument
  └──→ DocumentVersion[] (versioned content from git)
         └──→ DocumentTranslation[] (reference translations)

Team
  └──→ TeamGoogleAccess[] ──→ GoogleResource

Role
  └──→ RoleGoogleAccess[] ──→ GoogleResource
```

### Core Models

#### User (accounts app)
Custom user model - **must be created before first migration**.

```python
class User(AbstractBaseUser, PermissionsMixin):
    email = EmailField(unique=True)              # Google account email (primary key)
    display_name = CharField(max_length=255)
    preferred_language = CharField(max_length=5, default='en')
    date_joined = DateTimeField(auto_now_add=True)
    is_active = BooleanField(default=True)
    is_staff = BooleanField(default=False)       # Django admin access

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['display_name']
```

#### Profile (members app)
```python
class Profile(models.Model):
    user = OneToOneField(User, on_delete=CASCADE)
    legal_name = CharField(max_length=255)       # Required by statutes Art. 26
    country_of_residence = CharField(max_length=2)  # ISO 3166-1 alpha-2
    created_at = DateTimeField(auto_now_add=True)
    updated_at = DateTimeField(auto_now=True)

    @property
    def membership_status(self):
        """Computed from role assignments + document compliance"""
        # Returns: NONE, PENDING, APPROVED_PENDING_DOCUMENTS,
        #          ACTIVE, RESTRICTED, EXPIRED, REMOVED
```

#### RoleAssignment (members app)
```python
class RoleAssignment(models.Model):
    profile = ForeignKey(Profile, on_delete=CASCADE)
    role = CharField(choices=['COLABORADOR', 'ASOCIADO', 'BOARD_MEMBER'])
    start_date = DateField()
    end_date = DateField()                       # start_date + 2 years
    is_active = BooleanField(default=True)
    assigned_by = ForeignKey(User, null=True)
    notes = TextField(blank=True)

    history = HistoricalRecords()
```

#### Application (applications app)
```python
class Application(models.Model):
    user = ForeignKey(User, on_delete=CASCADE)

    # Application data
    legal_name = CharField(max_length=255)
    preferred_name = CharField(max_length=255, blank=True)
    country_of_residence = CharField(max_length=2)
    role_requested = CharField(choices=['COLABORADOR', 'ASOCIADO'])
    motivation = TextField()
    skills = TextField(blank=True)

    # Workflow (django-fsm)
    status = FSMField(default='SUBMITTED')
    # States: SUBMITTED → UNDER_REVIEW → APPROVED / REJECTED

    batch = ForeignKey('ApplicationBatch', null=True)
    submitted_at = DateTimeField(auto_now_add=True)

    # GDPR consent for application processing
    data_processing_consent = BooleanField(default=False)
    data_processing_consent_at = DateTimeField(null=True)

    history = HistoricalRecords()
```

#### LegalDocument (documents app)
```python
class LegalDocument(models.Model):
    slug = SlugField(unique=True)                # e.g., 'privacy-policy'
    title = CharField(max_length=255)
    document_type = CharField(choices=[
        'PRIVACY_POLICY', 'GDPR_DATA_PROCESSING', 'CONFIDENTIALITY',
        'CODE_OF_CONDUCT', 'INTERNAL_REGULATIONS', 'OTHER'
    ])
    is_required_for_activation = BooleanField(default=True)
    required_for_roles = JSONField(default=list)
    is_active = BooleanField(default=True)


class DocumentVersion(models.Model):
    document = ForeignKey(LegalDocument, on_delete=CASCADE)
    version_number = CharField(max_length=20)    # e.g., "1.0", "2.1"
    effective_date = DateField()

    # Content (synced from git)
    spanish_content = TextField()                # Legally binding
    content_hash = CharField(max_length=64)      # SHA-256 of content

    # Git provenance
    git_commit_sha = CharField(max_length=40)
    git_file_path = CharField(max_length=255)
    synced_at = DateTimeField()

    requires_re_consent = BooleanField(default=False)
    re_consent_deadline = DateField(null=True)
    is_current = BooleanField(default=False)


class ConsentRecord(models.Model):
    """IMMUTABLE - never update or delete"""
    profile = ForeignKey(Profile, on_delete=CASCADE)
    document_version = ForeignKey(DocumentVersion, on_delete=PROTECT)
    consented_at = DateTimeField(auto_now_add=True)
    ip_address = GenericIPAddressField()
    user_agent = TextField()
    consent_text_shown = TextField()
    language_viewed = CharField(max_length=5)
    is_active = BooleanField(default=True)
```

#### Google Integration (google_sync app)
```python
class GoogleResource(models.Model):
    name = CharField(max_length=255)
    resource_type = CharField(choices=['DRIVE', 'FOLDER', 'DOCUMENT'])
    google_id = CharField(max_length=255, unique=True)
    default_permission_role = CharField(choices=['reader', 'writer', 'commenter'])


class RoleGoogleAccess(models.Model):
    role = CharField(choices=ROLE_CHOICES)
    google_resource = ForeignKey(GoogleResource, on_delete=CASCADE)
    permission_role = CharField(choices=['reader', 'writer', 'commenter'])


class TeamGoogleAccess(models.Model):
    team = ForeignKey(Team, on_delete=CASCADE)
    google_resource = ForeignKey(GoogleResource, on_delete=CASCADE)
    permission_role = CharField(choices=['reader', 'writer', 'commenter'])


class GooglePermissionLog(models.Model):
    """Audit log of all Google permission changes"""
    profile = ForeignKey(Profile, on_delete=CASCADE)
    google_resource = ForeignKey(GoogleResource, on_delete=CASCADE)
    action = CharField(choices=['GRANT', 'REVOKE'])
    status = CharField(choices=['SUCCESS', 'FAILED', 'PENDING_RETRY'])
    google_permission_id = CharField(max_length=255, blank=True)
    attempted_at = DateTimeField(auto_now_add=True)
    error_message = TextField(blank=True)
    triggered_by = CharField(max_length=50)
```

---

## Legal Document Sync (from Git)

Legal documents are maintained in `nobodies-collective/legal` repository.

### Sync Flow

```
┌──────────────────┐     ┌─────────────────┐     ┌──────────────────┐
│ nobodies-        │     │  Profiles App   │     │  DocumentVersion │
│ collective/legal │────→│  Sync Service   │────→│    (Database)    │
│    (GitHub)      │     │                 │     │                  │
└──────────────────┘     └─────────────────┘     └──────────────────┘
        │                        │
        │ - Versioned docs       │ - Fetch on schedule
        │ - Translations         │ - Or webhook trigger
        │ - Git history          │ - Store with SHA
```

### Git Repo Structure (expected)

```
nobodies-collective/legal/
├── privacy-policy/
│   ├── es.md              # Spanish (canonical)
│   ├── en.md              # English translation
│   └── metadata.json      # version, effective_date, requires_re_consent
├── code-of-conduct/
│   ├── es.md
│   └── en.md
└── ...
```

### Sync Behavior

1. **Periodic sync** (celery-beat, daily) or **webhook** (GitHub → profiles)
2. Fetch latest from `main` branch
3. For each document directory:
   - Read `metadata.json` for version info
   - Hash Spanish content
   - If hash differs from current version → create new DocumentVersion
   - Store git commit SHA for provenance
4. If `requires_re_consent: true` in metadata → mark existing consents as needing renewal

---

## Membership Status State Machine

```
                    ┌─────────┐
                    │  NONE   │ (has account, no application)
                    └────┬────┘
                         │ submit application
                         ▼
                    ┌─────────┐
                    │ PENDING │ (application under review)
                    └────┬────┘
              ┌──────────┼──────────┐
              │ reject   │ approve  │
              ▼          │          ▼
         ┌────────┐      │    ┌─────────────────────────┐
         │REJECTED│      │    │APPROVED_PENDING_DOCUMENTS│
         └────────┘      │    └────────────┬────────────┘
                         │                 │ sign all docs
                         │                 ▼
                         │           ┌──────────┐
                         │           │  ACTIVE  │◄────────────┐
                         │           └────┬─────┘             │
                         │                │                   │
                    ┌────┴────────────────┴────┐              │
                    │                          │              │
            miss deadline            membership expires       │
                    │                          │              │
                    ▼                          ▼              │
              ┌──────────┐              ┌─────────┐          │
              │RESTRICTED│              │ EXPIRED │          │
              └────┬─────┘              └────┬────┘          │
                   │ re-consent              │ renew         │
                   └─────────────────────────┴───────────────┘
                                       │
                              board removes (Art. 25)
                                       │
                                       ▼
                                ┌─────────┐
                                │ REMOVED │
                                └─────────┘
```

---

## Background Tasks (Celery)

### Triggered Tasks

| Task | Trigger | Action |
|------|---------|--------|
| `send_application_confirmation` | Application submitted | Email applicant |
| `send_approval_notification` | Application approved | Email with login link |
| `provision_google_access` | Status → ACTIVE | Grant role-based Google resources |
| `revoke_google_access` | Status → RESTRICTED/EXPIRED/REMOVED | Revoke ALL Google permissions |
| `generate_data_export` | DataAccessRequest created | Build GDPR export ZIP |

### Scheduled Tasks (celery-beat)

| Task | Schedule | Action |
|------|----------|--------|
| `sync_legal_documents` | Daily 02:00 UTC | Sync from git repo |
| `check_expiring_memberships` | Daily 06:00 UTC | Send reminders at 60/30/7/0 days |
| `reconcile_google_permissions` | Daily 03:00 UTC | Fix drift between desired/actual |
| `enforce_consent_deadlines` | Daily 00:00 UTC | Set overdue → RESTRICTED |
| `cleanup_rejected_applications` | Weekly Sun 02:00 | Anonymize after 6 months |

---

## GDPR Compliance

### Principles Implemented

1. **Data minimization**: Only collect legally required fields
2. **Consent tracking**: Immutable ConsentRecord with timestamp, IP, exact text
3. **Right to access**: Export all personal data as ZIP
4. **Right to erasure**: Anonymization workflow (not hard delete)
5. **Audit trail**: django-simple-history + AuditLog model

### Retention Periods

| Data | Retention | Action |
|------|-----------|--------|
| Rejected applications | 6 months | Auto-anonymize |
| Expired memberships | 5 years | Offer anonymization |
| Audit logs | 5 years minimum | Archive |
| GDPR export files | 30 days | Auto-delete |

---

## Environment Variables

```bash
# Django
DJANGO_SECRET_KEY=
DJANGO_ALLOWED_HOSTS=profiles.nobodies.team
DJANGO_DEBUG=False

# Database
DATABASE_URL=postgres://user:pass@db:5432/nobodies

# Redis
REDIS_URL=redis://redis:6379/0

# Google OAuth (user login)
GOOGLE_OAUTH_CLIENT_ID=
GOOGLE_OAUTH_CLIENT_SECRET=

# Google Service Account (Drive API)
GOOGLE_SERVICE_ACCOUNT_JSON=

# Email (SMTP)
EMAIL_HOST=
EMAIL_PORT=587
EMAIL_HOST_USER=
EMAIL_HOST_PASSWORD=
EMAIL_USE_TLS=True
DEFAULT_FROM_EMAIL=noreply@nobodies.team

# Legal docs git repo
LEGAL_DOCS_REPO=nobodies-collective/legal
LEGAL_DOCS_BRANCH=main
GITHUB_TOKEN=  # For private repo access, if needed
```

---

## Security Considerations

1. **No username/password auth** - Google OAuth only
2. **HTTPS required** - Enforced by traefik
3. **CSRF protection** - Django default
4. **Rate limiting** - traefik middleware
5. **CSP headers** - Configured in Django
6. **Audit logging** - All sensitive operations logged
7. **Consent immutability** - ConsentRecord is append-only
