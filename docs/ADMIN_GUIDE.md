# Nobodies Profiles - Administrator Guide

This guide is for board members and administrators who need to manage the membership system. You don't need to be a developer, but basic computer skills are helpful.

## Table of Contents

1. [Key Concepts](#key-concepts)
2. [Accessing the Admin Panel](#accessing-the-admin-panel)
3. [Managing Members](#managing-members)
4. [Managing Applications](#managing-applications)
5. [Managing Legal Documents](#managing-legal-documents)
6. [Managing Teams](#managing-teams)
7. [Community Tags](#community-tags)
8. [GDPR & Data Requests](#gdpr--data-requests)
9. [Google Drive Access](#google-drive-access)
10. [Common Tasks](#common-tasks)
11. [Troubleshooting](#troubleshooting)

---

## Key Concepts

### Membership Status

Every member has a **computed status** based on their situation:

| Status | What it Means |
|--------|---------------|
| **NONE** | No membership - hasn't applied or was rejected |
| **PENDING** | Application submitted, waiting for board review |
| **APPROVED_PENDING_DOCUMENTS** | Application approved, but hasn't signed required documents yet |
| **ACTIVE** | Full member - approved and all documents signed |
| **RESTRICTED** | Was active, but needs to re-sign updated documents |
| **EXPIRED** | Membership period ended (roles last 2 years) |
| **REMOVED** | Removed by board decision |

> **Important:** You cannot set status directly. It's calculated automatically based on role assignments and document signatures.

### Roles

Members can have one of three roles:

| Role | Description |
|------|-------------|
| **COLABORADOR** | Volunteer/collaborator - basic participation |
| **ASOCIADO** | Full member with voting rights |
| **BOARD_MEMBER** | Board member with administrative access |

Roles are assigned for **2 years** (per statute Art. 20.3) and must be renewed.

### Legal Documents

Documents that members must sign, such as:
- Privacy Policy
- Code of Conduct
- Confidentiality Agreement

Spanish versions are **legally binding**. English and other translations are for reference only.

---

## Accessing the Admin Panel

1. Go to: `https://profiles.nobodies.team/admin/`
2. Log in with your Google account (must be a board member)
3. You'll see the admin dashboard with all manageable sections

### Admin Sections Overview

| Section | What You Manage |
|---------|-----------------|
| **Accounts > Users** | User accounts (email, active status) |
| **Members > Profiles** | Member profiles and role assignments |
| **Members > Teams** | Working groups and team membership |
| **Members > Community Tags** | Ornamental tags for members |
| **Applications** | Membership applications |
| **Documents** | Legal documents and consent tracking |
| **GDPR** | Data export and deletion requests |
| **Google Access** | Drive permissions (if configured) |

---

## Managing Members

### View All Members

1. Go to **Members > Profiles**
2. You'll see a list with: Name, Email, Country, Role, Status, Join Date
3. Use the search box to find specific members
4. Use filters on the right to filter by country or date

### View a Member's Details

1. Click on a member's name
2. You'll see:
   - **Basic info**: Legal name, country, user account link
   - **Status**: Current computed membership status
   - **Role Assignments**: Current and past roles (inline at bottom)
   - **Tags**: Community tags assigned to this member

### Assign a Role to a Member

1. Open the member's profile
2. Scroll to **Role Assignments** section
3. Click **Add another Role Assignment**
4. Fill in:
   - **Role**: Select COLABORADOR, ASOCIADO, or BOARD_MEMBER
   - **Start date**: When the role begins
   - **End date**: Auto-calculated as start + 2 years (can override)
   - **Assigned by**: Select yourself
   - **Notes**: Optional reason for assignment
5. Click **Save**

### Deactivate a Member

To remove someone's active membership:

1. Open their profile
2. Find their active Role Assignment
3. Uncheck **Active**
4. Add a note explaining why (e.g., "Resigned", "Removed by board vote")
5. Click **Save**

Their status will automatically change to EXPIRED or REMOVED.

### Export Member List

1. Go to **Members > Profiles**
2. Select members using checkboxes (or select all)
3. From the **Action** dropdown, choose **Export selected profiles**
4. Choose format (CSV, Excel, etc.)
5. Click **Go**

---

## Managing Applications

### View Pending Applications

1. Go to **Applications > Applications**
2. Filter by **Status = SUBMITTED** or **UNDER_REVIEW**
3. Click on an application to review it

### Review an Application

1. Open the application
2. Review the applicant's information:
   - Legal name, country, preferred language
   - Role requested (Colaborador or Asociado)
   - How they heard about us
   - Their motivation and skills
   - Whether they've attended events before
3. To **approve**:
   - Change status to **UNDER_REVIEW** first (if SUBMITTED)
   - Then change to **APPROVED**
   - Fill in review notes
   - Click Save
   - A profile will be created automatically
4. To **reject**:
   - Change status to **REJECTED**
   - Fill in review notes explaining why
   - Click Save

### Application Workflow

```
SUBMITTED → UNDER_REVIEW → APPROVED or REJECTED
```

- **SUBMITTED**: Just received, not yet looked at
- **UNDER_REVIEW**: Board is reviewing
- **APPROVED**: Creates a Profile and Role Assignment
- **REJECTED**: Application denied (can reapply later)

---

## Managing Legal Documents

### Understanding Document Structure

```
Legal Document (e.g., "Privacy Policy")
  └── Document Version (e.g., "v1.0")
        ├── Spanish Content (legally binding)
        └── Translations (reference only)
              ├── English
              ├── French
              └── etc.
```

### View Current Documents

1. Go to **Documents > Legal Documents**
2. You'll see all documents with their current version
3. Click on a document to see details and all versions

### Create a New Document

1. Go to **Documents > Legal Documents**
2. Click **Add Legal Document**
3. Fill in:
   - **Title**: e.g., "Code of Conduct"
   - **Slug**: URL-friendly name, e.g., "code-of-conduct" (auto-fills)
   - **Document type**: Select from dropdown
   - **Required for activation**: Check if members must sign to become ACTIVE
   - **Required for roles**: Leave empty for all roles, or select specific roles
   - **Display order**: Lower numbers show first
4. Click **Save**
5. Now add a version (see below)

### Add a Document Version

1. Open the Legal Document
2. In the **Document Versions** section, click **Add another Document Version**
3. Fill in:
   - **Version number**: e.g., "1.0"
   - **Effective date**: When it takes effect
   - **Spanish content**: The full legal text in Spanish (required!)
   - **Is current**: Check this to make it the active version
   - **Changelog**: What changed from previous version
4. Click **Save**

### Add a Translation

1. Go to **Documents > Document Versions**
2. Find and open the version you want to translate
3. In the **Translations** section, click **Add another Document Translation**
4. Fill in:
   - **Language**: Select language
   - **Content**: The translated text
   - **Is machine translated**: Check if you used Google Translate, etc.
5. Click **Save**

### Require Re-consent for Updated Document

When you update a document and need members to sign again:

1. Create a new Document Version (e.g., "1.1")
2. Check **Requires re-consent**
3. Set **Re-consent deadline**: Date by which members must sign
4. Check **Is current** to make it active
5. Click **Save**

Members who signed the old version will:
- See the new document in their dashboard
- Have status changed to RESTRICTED if they miss the deadline

---

## Managing Teams

Teams are working groups within the organization (e.g., "Communications", "Events").

### Create a Team

1. Go to **Members > Teams**
2. Click **Add Team**
3. Fill in:
   - **Name**: Team name
   - **Slug**: URL-friendly name (auto-fills)
   - **Description**: What this team does
   - **Active**: Check to make it active
4. Click **Save**

### Add Members to a Team

1. Open the team
2. In **Team Memberships**, click **Add another Team Membership**
3. Select:
   - **Profile**: Search for the member
   - **Role in team**: MEMBER or LEAD
   - **Added by**: Select yourself
4. Click **Save**

### Remove Someone from a Team

1. Open the team
2. Find their Team Membership
3. Uncheck **Active**
4. Click **Save**

---

## Community Tags

Tags are labels you can assign to members for identification (e.g., "Camp Lead", "Freecamper"). They're purely decorative - they don't affect permissions or access.

### Create a Tag

1. Go to **Members > Community Tags**
2. Click **Add Community Tag**
3. Fill in:
   - **Name**: Display name (e.g., "Camp Lead")
   - **Slug**: URL-friendly (e.g., "camp-lead")
   - **Category**: EVENT, SKILL, RECOGNITION, or INTEREST
   - **Color**: Hex color code (e.g., "#FF5733" for orange)
   - **Icon**: CSS icon class (optional)
   - **Self-assignable**: Can members add this tag themselves?
   - **Display order**: Lower numbers appear first
4. Click **Save**

### Assign a Tag to a Member

**Method 1 - From the tag:**
1. Go to **Members > Profile Tags**
2. Click **Add Profile Tag**
3. Select the profile and tag
4. Click **Save**

**Method 2 - From the member's profile:**
1. Open the member's profile
2. In **Profile Tags** section, click **Add another Profile Tag**
3. Select the tag
4. Click **Save**

---

## GDPR & Data Requests

### Data Export Requests

Members can request a download of all their personal data.

1. Go to **GDPR > Data Access Requests**
2. You'll see all requests with status:
   - **PENDING**: Just requested
   - **PROCESSING**: Export being generated
   - **COMPLETED**: Ready to download
   - **EXPIRED**: Download link expired (30 days)

Exports are generated automatically - no action needed from you.

### Data Deletion Requests

Members can request account deletion. These require board review.

1. Go to **GDPR > Data Deletion Requests**
2. Filter by **Status = UNDER_REVIEW** to see pending requests
3. Click on a request to review
4. You'll see:
   - Member's name and request reason
   - When they submitted and confirmed
5. To **approve**: Select the request, use Action dropdown → "Approve selected"
6. To **deny**: Use "Deny selected" and provide a reason

**What happens when approved:**
- User's email becomes `deleted_xxx@deleted.nobodies.team`
- Legal name becomes `Deleted User #xxx`
- Personal data in applications is redacted
- Role assignments and team memberships are deactivated
- Google Drive access is revoked
- Consent records are marked inactive (not deleted - legally required)

### View Audit Log

All significant actions are logged for compliance.

1. Go to **GDPR > Audit Logs**
2. You can filter by:
   - Category (AUTH, CONSENT, DATA_EXPORT, etc.)
   - Date range
   - Search text
3. Audit logs **cannot be edited or deleted** - this is intentional for legal compliance

---

## Google Drive Access

If Google Drive integration is configured, you can manage who has access to shared drives and folders.

### How It Works

1. **Google Resources**: Shared drives, folders, or files you want to manage
2. **Role-based Access**: "All board members get access to X"
3. **Team-based Access**: "Everyone on the Events team gets access to Y"

Access is granted automatically when:
- A member becomes ACTIVE
- A member joins a team
- A reconciliation job runs (daily)

Access is revoked when:
- A member's status is no longer ACTIVE
- A member leaves a team
- A member's account is deleted

### Add a Google Resource

1. Go to **Google Access > Google Resources**
2. Click **Add**
3. Fill in:
   - **Name**: Friendly name
   - **Resource type**: SHARED_DRIVE, FOLDER, or FILE
   - **Google ID**: The ID from the Drive URL
4. Click **Save**

### Grant Access by Role

1. Go to **Google Access > Role Google Access**
2. Click **Add**
3. Select:
   - **Role**: COLABORADOR, ASOCIADO, or BOARD_MEMBER
   - **Resource**: The Google resource
   - **Permission**: reader, commenter, writer, or organizer
4. Click **Save**

### Grant Access by Team

1. Go to **Google Access > Team Google Access**
2. Click **Add**
3. Select the team, resource, and permission level
4. Click **Save**

---

## Common Tasks

### "How do I add a new member?"

1. Have them apply at `https://profiles.nobodies.team/applications/apply/`
2. Review their application in Admin > Applications
3. Approve it - a profile is created automatically
4. They'll need to sign required documents to become ACTIVE

### "How do I make someone a board member?"

1. Go to their profile in Admin
2. Add a new Role Assignment with role = BOARD_MEMBER
3. They'll now have admin access

### "How do I see who signed a document?"

1. Go to **Documents > Consent Records**
2. Filter by the document version
3. You'll see who signed, when, and from what IP

### "How do I remove someone completely?"

1. Deactivate their role assignment (see Managing Members)
2. If they request deletion, approve their GDPR deletion request
3. Their data will be anonymized but structure preserved

### "How do I extend someone's membership?"

1. Open their profile
2. Edit their Role Assignment
3. Change the **End date** to the new expiration date
4. Click **Save**

### "How do I see membership statistics?"

1. Go to **Members > Profiles**
2. The list shows all members
3. Use filters to count by status, country, etc.
4. Export to CSV/Excel for detailed analysis

---

## Troubleshooting

### "Member shows APPROVED_PENDING_DOCUMENTS but they signed everything"

1. Check if there are newer document versions requiring re-consent
2. Go to **Documents > Consent Records** and verify their signatures
3. Make sure the Document Version has **Is current** checked

### "I can't access the admin panel"

1. Verify you're logged in with your Google account
2. Check that your profile has a BOARD_MEMBER role assignment
3. Make sure the role is **Active** and dates are current

### "A member's Google Drive access isn't working"

1. Check their membership status is ACTIVE
2. Verify the Google Resource exists and is active
3. Check Role/Team Google Access rules include them
4. Wait for the daily reconciliation job, or contact technical admin

### "I accidentally rejected an application"

Applications can't be un-rejected through the admin. Options:
1. Have them apply again
2. Ask a technical admin to change the status directly in the database

### "The audit log shows something I don't understand"

Each entry has:
- **Timestamp**: When it happened
- **User**: Who did it (or "System" for automated actions)
- **Category**: Type of action
- **Action**: Specific action code
- **Description**: Human-readable explanation

Contact the technical team if you need more details about a specific entry.

---

## Getting Help

- **Technical issues**: Contact the technical administrator
- **Policy questions**: Discuss with the board
- **Bug reports**: File at https://github.com/nobodies-collective/profiles/issues

---

*Last updated: February 2026*
