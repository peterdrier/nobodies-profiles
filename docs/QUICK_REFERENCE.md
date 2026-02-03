# Quick Reference Card

Print this page and keep it handy!

## Member Status Flow

```
[No Account] → Apply → [PENDING] → Board Approves → [APPROVED_PENDING_DOCUMENTS]
                                                            ↓
                                                    Signs Documents
                                                            ↓
                                                       [ACTIVE]
                                                            ↓
                                            Document Update Requires Re-sign
                                                            ↓
                                                     [RESTRICTED]
                                                            ↓
                                                    Signs New Version
                                                            ↓
                                                       [ACTIVE]
```

## Application Workflow

```
SUBMITTED → UNDER_REVIEW → APPROVED (creates profile)
                        → REJECTED
```

## Common Admin URLs

| Task | URL |
|------|-----|
| Admin Home | `/admin/` |
| All Members | `/admin/members/profile/` |
| Applications | `/admin/applications/application/` |
| Legal Documents | `/admin/documents/legaldocument/` |
| Consent Records | `/admin/documents/consentrecord/` |
| Teams | `/admin/members/team/` |
| Community Tags | `/admin/members/communitytag/` |
| GDPR Requests | `/admin/gdpr/datadeletionrequest/` |
| Audit Log | `/admin/gdpr/auditlog/` |

## Role Permissions

| Role | Can Access Admin | Duration |
|------|------------------|----------|
| COLABORADOR | No | 2 years |
| ASOCIADO | No | 2 years |
| BOARD_MEMBER | Yes | 2 years |

## Document Types

- `PRIVACY_POLICY` - Privacy policy
- `GDPR_DATA_PROCESSING` - Data processing agreement
- `CONFIDENTIALITY` - Confidentiality agreement
- `CODE_OF_CONDUCT` - Code of conduct
- `INTERNAL_REGULATIONS` - Internal rules
- `OTHER` - Other documents

## Tag Categories

- `EVENT` - Event-related (e.g., "Freecamper")
- `SKILL` - Skills (e.g., "DJ", "Cook")
- `RECOGNITION` - Recognition (e.g., "Camp Lead")
- `INTEREST` - Interests (e.g., "Art", "Music")

## GDPR Request Status

**Data Export:**
```
PENDING → PROCESSING → COMPLETED → EXPIRED (after 30 days)
                    → FAILED
```

**Data Deletion:**
```
REQUESTED → PENDING_CONFIRMATION → UNDER_REVIEW → APPROVED → EXECUTING → EXECUTED
                                               → DENIED
                                                          → FAILED
```

## Keyboard Shortcuts in Admin

- `Ctrl+S` / `Cmd+S` - Save (in most browsers)
- `Tab` - Move to next field
- `Shift+Tab` - Move to previous field

## Emergency Contacts

- **Technical Admin**: [your-tech-contact]
- **Board Chair**: [board-chair-contact]

---

*Keep this reference handy! Full guide: `/docs/ADMIN_GUIDE.md`*
