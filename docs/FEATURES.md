# Application Features

This document provides an overview of the major features in this Django membership management system for developers.

## Core Features

### 1. Member Management
- Custom User model with email-based authentication
- Google OAuth integration via django-allauth
- Profile management with computed membership status
- Role assignments with audit trails (django-simple-history)

### 2. Application Workflow
- FSM (Finite State Machine) based application processing
- States: SUBMITTED → UNDER_REVIEW → APPROVED
- Approval triggers automatic Profile and RoleAssignment creation

### 3. Legal Document & Consent System
- Legal documents synced from a separate git repository
- Version-controlled document management
- Append-only ConsentRecord table (legally compliant - no updates/deletes)
- Consent revocation tracked via separate ConsentRevocation records
- Spanish content is legally binding; translations are reference-only

### 4. Team Management
- Working groups and team memberships
- Team-based access control

### 5. Google Workspace Integration
- Google Drive permission provisioning via API
- Role-based and Team-based Google resource access
- Reconciliation job for syncing permissions
- Celery-based with rate limiting and exponential backoff

### 6. GDPR Compliance
- Personal data export functionality
- Data anonymization requests
- Consent tracking with full audit trail
- IP anonymization (planned)

### 7. Internationalization
- Multi-language support (Spanish primary, English, with French/German/Portuguese planned)
- URL-prefixed language routing (`/es/`, `/en/`)

## Tech Stack

- **Framework**: Django 5.x
- **Database**: PostgreSQL 16
- **Cache/Broker**: Redis 7
- **Task Queue**: Celery
- **Deployment**: Docker Compose with Traefik
- **Key Libraries**:
  - django-allauth (OAuth)
  - django-fsm (workflows)
  - django-simple-history (auditing)
  - google-api-python-client (Drive API)
