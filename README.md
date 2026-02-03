# Nobodies Profiles

Membership management system for Asociación Nobodies Collective.

## Documentation

- **[ARCHITECTURE.md](ARCHITECTURE.md)** - Technical architecture, data models, infrastructure
- **[CLAUDE.md](CLAUDE.md)** - Instructions for Claude Code when working on this project
- **[DEVELOPMENT_PLAN.md](DEVELOPMENT_PLAN.md)** - Phased implementation plan

## Features

- Membership application and approval workflows
- Legal document consent tracking (GDPR-compliant)
- Google Drive access provisioning
- Team/working group organization
- Multi-language support (Spanish primary, English, French, German, Portuguese)

## Tech Stack

- Django 5.x
- PostgreSQL 16
- Redis 7
- Celery
- Docker Compose

## Quick Start

```bash
# Start services
docker compose up -d

# Run migrations
docker compose exec web python manage.py migrate

# Create superuser
docker compose exec web python manage.py createsuperuser
```

## Legal

Legal documents are maintained in the [nobodies-collective/legal](https://github.com/nobodies-collective/legal) repository and synced automatically.

## License

TBD
