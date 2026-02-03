# Development Plan - Nobodies Profiles

Phased implementation plan for the membership management system.

---

## Pre-Development Setup

### Repository Setup
- [ ] Re-authenticate gh CLI: `gh auth login -h github.com`
- [ ] Create repo: `gh repo create peterdrier/nobodies-profiles --public`
- [ ] Initialize with README, .gitignore (Python/Django)

### Legal Docs Repo
- [ ] Create `nobodies-collective/legal` repo (or verify access)
- [ ] Define document structure (see ARCHITECTURE.md)
- [ ] Add initial documents: Privacy Policy, Code of Conduct

### Infrastructure
- [ ] Add `nobodies.team` domain to traefik cert config (when ready for public)
- [ ] Create DNS record pointing to NUC (when ready)
- [ ] For dev: use `profiles.i.burn.camp` or localhost

---

## Phase 1: Foundation (MVP)

**Goal**: People can apply, board can review, approved members can log in.

### 1.1 Project Scaffold
- [ ] Django 5.x project with settings split (base/local/production)
- [ ] Custom User model in `accounts` app (email-based, no username)
- [ ] **Run initial migration immediately after User model**
- [ ] Docker Compose: web, db (postgres:16), redis
- [ ] Environment variable configuration
- [ ] Basic URL routing

### 1.2 Authentication
- [ ] Install and configure django-allauth
- [ ] Google OAuth provider setup
- [ ] Login/logout views
- [ ] Redirect unauthenticated users to login
- [ ] Post-login redirect to dashboard

### 1.3 Profile & Application Models
- [ ] Profile model (linked to User)
- [ ] Application model with FSM states (SUBMITTED, UNDER_REVIEW, APPROVED, REJECTED)
- [ ] ApplicationBatch model for grouping reviews
- [ ] django-simple-history on both models

### 1.4 Application Form (Public)
- [ ] Application form view (requires login)
- [ ] Fields: legal name, preferred name, country, role requested, motivation, skills
- [ ] GDPR consent checkbox (unchecked, required)
- [ ] Form validation and submission
- [ ] Create Application record on submit

### 1.5 Board Review Interface
- [ ] Board-only access (check is_staff or Board role)
- [ ] List pending applications
- [ ] Batch creation and assignment
- [ ] Individual application detail view
- [ ] Approve/reject actions with notes
- [ ] On approve: create Profile + placeholder RoleAssignment

### 1.6 Member Dashboard (Basic)
- [ ] Dashboard view showing status
- [ ] For NONE: "Apply here" link
- [ ] For PENDING: "Application under review"
- [ ] For APPROVED+: Show profile info

### 1.7 Email Notifications
- [ ] Email backend configuration (SMTP)
- [ ] Template: application_received (to applicant)
- [ ] Template: application_approved (to applicant)
- [ ] Template: application_rejected (to applicant)
- [ ] Celery task for async sending
- [ ] Translations: es, en

### 1.8 Basic i18n
- [ ] Django i18n setup (USE_I18N, LANGUAGES)
- [ ] Language middleware
- [ ] URL prefix pattern (/es/, /en/)
- [ ] Wrap existing strings in {% trans %}
- [ ] Compile message files

### Phase 1 Milestone Test
> A person visits the site, signs in with Google, submits an application, a board member approves it, the person sees their "approved" status.

---

## Phase 2: Legal Documents & Consent

**Goal**: Members must sign required documents before activation.

### 2.1 Document Models
- [ ] LegalDocument model (slug, title, type, required flags)
- [ ] DocumentVersion model (version, content, hash, git refs)
- [ ] DocumentTranslation model (language, content)
- [ ] ConsentRecord model (immutable)
- [ ] ConsentRevocation model

### 2.2 Git Sync Service
- [ ] Service to fetch from `nobodies-collective/legal` repo
- [ ] Parse document directories and metadata.json
- [ ] Create/update DocumentVersion records
- [ ] Store git commit SHA for provenance
- [ ] Celery task: `sync_legal_documents` (daily schedule)

### 2.3 Document Viewing UI
- [ ] Document view page
- [ ] Spanish content as primary
- [ ] Language selector for translations
- [ ] Clear disclaimer banner for translations
- [ ] Responsive layout for reading

### 2.4 Consent Workflow
- [ ] List pending documents on dashboard
- [ ] Consent form with explicit checkbox (unchecked)
- [ ] Consent text includes version, date, Spanish acknowledgment
- [ ] On submit: create ConsentRecord with IP, user agent, exact text
- [ ] Mark consent as active

### 2.5 Status Gate Logic
- [ ] Implement `Profile.membership_status` as computed property
- [ ] Check: has active RoleAssignment?
- [ ] Check: has active consent for all required documents?
- [ ] Status only becomes ACTIVE when both true
- [ ] Update dashboard to show APPROVED_PENDING_DOCUMENTS state

### 2.6 Board Document Management
- [ ] Admin interface for LegalDocument CRUD
- [ ] View document versions
- [ ] Manual "publish new version" (syncs from git on demand)
- [ ] Toggle requires_re_consent flag
- [ ] Set re_consent_deadline

### 2.7 Re-consent Campaign
- [ ] When new version with requires_re_consent published:
  - [ ] Find profiles with active consent to previous version
  - [ ] Set their consent.is_active = False
  - [ ] Send notification email
- [ ] Celery task: `send_consent_required_email`
- [ ] Celery beat: `send_consent_reminders` (7d, 1d before deadline)

### 2.8 Consent Deadline Enforcement
- [ ] Celery beat: `enforce_consent_deadlines`
- [ ] Find members past deadline without new consent
- [ ] Set status → RESTRICTED
- [ ] Send `consent_overdue` email

### 2.9 Compliance Dashboard (Board)
- [ ] View: who signed which document
- [ ] Filter by document, version, status
- [ ] Export to CSV

### Phase 2 Milestone Test
> Board publishes a Privacy Policy. New member sees it after approval, signs it, status becomes ACTIVE. Board publishes v2 with re-consent required. Member gets notified, signs new version, status remains ACTIVE. Another member misses deadline, status becomes RESTRICTED.

---

## Phase 3: Google Drive Integration

**Goal**: Active members get Drive access. Expired/restricted members lose it.

### 3.1 Google Service Account Setup
- [ ] Create GCP project (or use existing)
- [ ] Create service account with Drive API access
- [ ] Enable domain-wide delegation (if Workspace) or direct sharing
- [ ] Store credentials as env var or mounted secret

### 3.2 Google Resource Models
- [ ] GoogleResource model (Drive, Folder, Document)
- [ ] RoleGoogleAccess model (role → resources)
- [ ] TeamGoogleAccess model (team → resources)
- [ ] GooglePermissionLog model (audit trail)

### 3.3 Permission Grant/Revoke Functions
- [ ] `grant_permission(profile, resource, role)` - creates Drive permission
- [ ] `revoke_permission(profile, resource)` - removes Drive permission
- [ ] Handle rate limiting with exponential backoff
- [ ] Log all attempts in GooglePermissionLog

### 3.4 Triggered Provisioning
- [ ] Signal: on status → ACTIVE
- [ ] Celery task: `provision_google_access`
- [ ] Grant all RoleGoogleAccess resources for user's role
- [ ] Store google_permission_id for later revocation

### 3.5 Triggered Revocation
- [ ] Signal: on status → RESTRICTED/EXPIRED/REMOVED
- [ ] Celery task: `revoke_google_access`
- [ ] Revoke ALL permissions using stored permission IDs
- [ ] Log results

### 3.6 Teams
- [ ] Team model
- [ ] TeamMembership model (profile ↔ team, role_in_team)
- [ ] Admin interface for team management
- [ ] Assign members to teams

### 3.7 Team-Based Access
- [ ] On TeamMembership create: grant TeamGoogleAccess resources
- [ ] On TeamMembership deactivate: revoke team-specific resources only
- [ ] Celery tasks: `provision_team_google_access`, `revoke_team_google_access`

### 3.8 Daily Reconciliation
- [ ] Celery beat: `reconcile_google_permissions`
- [ ] Calculate desired state: active profiles × their role/team resources
- [ ] Fetch actual state from Google API (with pagination)
- [ ] Grant missing permissions, revoke extra ones
- [ ] Log all corrections
- [ ] Spread API calls over time (not burst)

### 3.9 Membership Expiry Handling
- [ ] RoleAssignment has end_date (start_date + 2 years)
- [ ] Celery beat: `check_expiring_memberships`
- [ ] Send reminders at 60/30/7/0 days before expiry
- [ ] On expiry day: deactivate RoleAssignment, status → EXPIRED, revoke access

### 3.10 Google Sync Status (Board)
- [ ] View recent sync logs
- [ ] Per-member sync status
- [ ] Manual "sync now" button (per person or global)
- [ ] Error log with retry controls

### Phase 3 Milestone Test
> Member approved + docs signed → gets writer access to Shared Drive. Added to "Production" team → gets access to Production folder. Membership expires → all access revoked. Re-enrolls → access restored.

---

## Phase 4: GDPR & Polish

**Goal**: Full GDPR compliance, production hardening.

### 4.1 Data Access Request (Art. 15)
- [ ] DataAccessRequest model
- [ ] Member self-service: "Download my data" button
- [ ] Board can also trigger for any member
- [ ] Celery task: `generate_data_export`
- [ ] Export includes: profile, roles, consents, teams, applications, google logs, audit entries
- [ ] Generate ZIP file, store temporarily
- [ ] Email member when ready with download link
- [ ] Auto-delete export files after 30 days

### 4.2 Data Deletion Request (Art. 17)
- [ ] DataDeletionRequest model (status: REQUESTED, APPROVED, EXECUTED, DENIED)
- [ ] Member self-service: "Request account deletion"
- [ ] Confirmation flow before submission
- [ ] Board review queue
- [ ] Denial requires documented reason

### 4.3 Anonymization Workflow
- [ ] On approved deletion request:
  - [ ] Revoke all Google access first
  - [ ] Anonymize profile fields (legal_name → "Deleted User #hash")
  - [ ] Anonymize email (hash@deleted.nobodies.team)
  - [ ] Null out country, skills, motivation, etc.
  - [ ] Preserve structural records with anonymized references
  - [ ] Log what was changed in DataDeletionRequest.anonymization_log
- [ ] Celery task: `execute_data_anonymization`

### 4.4 Audit Infrastructure
- [ ] AuditLog model for cross-cutting actions
- [ ] Log: logins, exports, API calls, admin actions
- [ ] Searchable/filterable audit log viewer (board)
- [ ] Ensure django-simple-history is on all critical models

### 4.5 Retention Policy Automation
- [ ] Celery beat: `cleanup_rejected_applications` (anonymize after 6 months)
- [ ] Celery beat: `cleanup_gdpr_exports` (delete after 30 days)
- [ ] Future: offer anonymization for 5+ year expired memberships

### 4.6 Record of Processing Activities
- [ ] Static page documenting all processing activities
- [ ] Purposes, data categories, retention periods
- [ ] Link from privacy policy / footer

### 4.7 GDPR Self-Service (Dashboard)
- [ ] "My Data" section on member dashboard
- [ ] Download my data button
- [ ] Request deletion button
- [ ] View pending requests

### 4.8 Board GDPR Dashboard
- [ ] Pending data access requests
- [ ] Pending deletion requests (with approve/deny)
- [ ] Retention report (data approaching retention limits)

### 4.9 Remaining Email Templates
- [ ] All templates in 5 languages (es, en, fr, de, pt)
- [ ] membership_expiring (60/30/7 day variants)
- [ ] membership_expired
- [ ] membership_renewed
- [ ] data_export_ready
- [ ] deletion_request_received
- [ ] deletion_executed

### 4.10 Security Hardening
- [ ] CSP headers (django-csp or middleware)
- [ ] Rate limiting on sensitive endpoints
- [ ] Security headers (X-Frame-Options, etc.)
- [ ] Review OWASP top 10 checklist
- [ ] Secrets management review

### 4.11 Production Deployment
- [ ] Production Docker Compose
- [ ] Traefik labels for profiles.nobodies.team
- [ ] Health check endpoint
- [ ] Logging configuration (structured JSON)
- [ ] Error reporting (Sentry or similar)
- [ ] Backup strategy for database

### Phase 4 Milestone Test
> Member requests data export → receives ZIP with all their data. Member requests deletion → board approves → profile anonymized, Google access revoked, structural records preserved with anonymized references.

---

## Future Enhancements (Post-MVP)

### SSO API Endpoint
```
GET /api/v1/verify/?email=someone@gmail.com
Authorization: Bearer <api-key>
```
For other org tools to check membership status.

### Additional Languages
- Add French (fr), German (de), Portuguese (pt) translations
- Crowdsourced translation workflow

### Member Directory
- Searchable directory for ACTIVE members
- Opt-in visibility controls

### Renewal Workflow
- Online renewal application
- Board bulk renewal processing

### Integration Hooks
- Webhook notifications for external systems
- Event bus for status changes

---

## Development Workflow

### Branch Strategy
- `main` - production-ready code
- `develop` - integration branch
- `feature/*` - feature branches
- `fix/*` - bug fix branches

### PR Process
1. Create feature branch from develop
2. Implement with tests
3. PR to develop with description
4. Review + CI pass
5. Squash merge

### Testing Requirements
- Unit tests for models and services
- Integration tests for workflows
- Minimum 80% coverage on new code

### Deployment Process
1. Merge develop → main
2. Tag release (semver)
3. CI builds and pushes Docker image
4. Update docker-compose on server
5. `docker compose pull && docker compose up -d`

---

## Estimated Effort

| Phase | Scope | Complexity |
|-------|-------|------------|
| Phase 1 | Core MVP | Medium |
| Phase 2 | Documents & Consent | Medium-High |
| Phase 3 | Google Integration | High |
| Phase 4 | GDPR & Production | Medium |

Each phase should be completable incrementally with working software at each milestone.
