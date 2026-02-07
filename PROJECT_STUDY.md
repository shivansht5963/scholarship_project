# Scholar Match - Project Study Guide

## Project Overview

**Scholar Match** is a Django-based scholarship management and matching platform designed to connect students with scholarships through AI-driven eligibility matching and moderator verification.

**Tech Stack:**
- Django 5.2.6
- SQLite3 (Development)
- Python
- HTML/Templates

---

## Architecture & Modules

### 1. **Core Project Configuration** (`scholar_match/`)
- **settings.py**: Main Django configuration
  - Custom User Model: `users.User`
  - SQLite database
  - 6 installed apps (Users, Scholarships, FunderPortal, Applications, Moderator Panel, AI Integrations)
  - Debug mode enabled (development)
  
- **urls.py**: Main URL router
  - `/accounts/` → User authentication and dashboard routing
  - `/moderator/` → Moderator panel
  - `/organization/` → Funder/Organization portal
  - Commented out: Scholarships, Applications, AI APIs

---

## Database Schema & Models

### **users/** - User Management & Profiles
**Models:**
1. **User** (Custom AbstractUser)
   - Extends Django's default User
   - Fields: `is_student`, `is_moderator`, `is_organization`
   - Role-based access control via boolean flags

2. **StudentProfile** (OneToOne with User)
   - Full name, DOB, Gender, Caste category
   - Annual income, disability status
   - Address and pin code
   - Created timestamp

3. **AcademicRecord** (ForeignKey to StudentProfile)
   - Multiple records per student
   - Degree level, stream, institution
   - Current year, last exam score (percentage/CGPA)

4. **ModeratorProfile** (OneToOne with User)
   - Organization name, contact phone
   - Verification status by platform admin

5. **OrganizationProfile** (OneToOne with User)
   - Organization name (unique), contact person
   - Official email (unique), website URL
   - Funder verification status

---

### **scholarships/** - Scholarship Management
**Models:**
1. **Scholarship**
   - Name (unique), organization, source URL
   - Deadline, award amount (as string), details
   - Active/verified status, last updated timestamp
   - **Issue**: `organization` is CharField, not ForeignKey to OrganizationProfile

2. **EligibilityCriteria** (ForeignKey to Scholarship)
   - Criterion type (e.g., MIN_INCOME, MAX_AGE, MIN_GPA)
   - Comparison operator (GT, LT, EQ, IN)
   - Value to check against
   - Required flag
   - Purpose: Rules for AI matching engine

3. **RequiredDocument** (ForeignKey to Scholarship)
   - Document name, description
   - Mandatory flag
   - Checklist of required files

---

### **applications/** - Scholarship Applications
**Models:**
1. **Application** (ForeignKey to StudentProfile & Scholarship)
   - Unique together constraint (student + scholarship)
   - Status workflow: DRAFT → PENDING_REVIEW → MOD_VERIFIED → SUBMITTED → APPROVED/REJECTED
   - Moderator assignment (nullable ForeignKey)
   - External application URL
   - Last action timestamp

2. **UploadedDocument** (ForeignKey to Application & RequiredDocument)
   - File storage: `application_docs/` (requires MEDIA settings)
   - AI verification status: PENDING, AI_OK, AI_FLAG, MOD_OK
   - Moderator verification & notes
   - Upload timestamp

3. **ApplicationRoadmapStep** (ForeignKey to Application)
   - Visual progress tracker
   - Step order, name, instructions
   - Completion status
   - Ordered by step_order

---

### **moderator_panel/** - Moderator Operations
**Models:**
1. **ModeratorActivityLog** (ForeignKey to ModeratorProfile & Application)
   - Action types: VERIFY_DOC, CHANGE_STATUS, NOTE_ADD, ASSIGN_APP
   - Details and timestamp
   - Audit trail for moderation actions

2. **TaskAssignment** (ForeignKey to ModeratorProfile, OneToOne to Application)
   - One-to-one ensures single moderator per application review
   - Assignment date, due date
   - Completion status

---

### **funder_portal/** - Currently Empty
- No models defined yet
- Will likely contain organization-specific analytics or application review queues

---

### **ai_integrations/** - AI Features Logging
**Models:**
1. **AICheckLog** (ForeignKey to Application)
   - Check types: ELIGIBILITY, DOCUMENT_OCR
   - Input data (JSON snapshot of student profile)
   - Result data (JSON with match score, OCR text, etc.)
   - Success flag, timestamp
   - Purpose: Audit trail for AI features

---

## Views & Business Logic

### **users/views.py**
- `smart_dashboard_redirect()`: Redirects to appropriate dashboard based on role
  - Moderator → `moderator_dashboard`
  - Organization → `funder_dashboard`
  - Student → `student_dashboard` (not yet implemented)

### **moderator_panel/views.py**
1. `is_moderator()`: User check function
2. `moderator_dashboard()`: Shows stats
   - Unassigned applications count
   - Moderator's pending tasks
   - Scholarships pending verification
3. `add_scholarship()`: Form-based scholarship creation
   - Default: not verified (`is_verified=False`)
   - Returns to dashboard after save

### **funder_portal/views.py**
1. `is_organization()`: User check function
2. `funder_dashboard()`: Organization dashboard
   - Shows organization profile
   - Lists organization's scholarships
   - Placeholder for total applications
3. `manage_scholarship()`: Create/Edit scholarships
   - Checks ownership (organization can only edit their own)
   - Auto-assigns organization on save
   - **Bug**: Sets both `organization` (ForeignKey reference) and `funder` (string) fields

---

## Forms

### **moderator_panel/forms.py**
- `ScholarshipForm`: ModelForm for scholarship creation
  - Includes all fields except verification status
  - Custom widgets: date input for deadline, textarea for details

### **funder_portal/forms.py**
- `FunderScholarshipForm`: ModelForm for organizations
  - Same fields as moderator form
  - Excludes organization field (set automatically)
  - **Issue**: Comment says "DO NOT include organization" but the field list includes it

---

## URL Routing Map

```
/accounts/login/              → Django auth login (template: users/login.html)
/accounts/logout/             → Django auth logout
/accounts/dashboard/          → smart_dashboard_redirect (router)

/moderator/dashboard/         → moderator_dashboard
/moderator/scholarships/add/  → add_scholarship

/organization/dashboard/      → funder_dashboard
/organization/scholarship/new/       → manage_scholarship (create)
/organization/scholarship/edit/<id>/ → manage_scholarship (edit)
```

---

## Templates

### Root `templates/`
- `base.html`: Base template (likely not implemented yet)

### `users/templates/users/`
- `login.html`: Login page

### `moderator_panel/templates/moderator_panel/`
- `moderator_dashboard.html`: Moderator dashboard
- `add_scholarship.html`: Scholarship creation form

### `funder_portal/templates/funder_portal/`
- `funder_dashboard.html`: Organization dashboard
- `manage_scholarship.html`: Create/Edit scholarship form

---

## Workflow & User Flows

### **Student Flow**
1. Register as Student (creates `StudentProfile`)
2. Fill academic and profile information
3. Browse scholarships
4. Apply for scholarship → Creates `Application` (DRAFT status)
5. Upload required documents → `UploadedDocument` records
6. Wait for moderator verification
7. Moderator verifies → Application moves to MOD_VERIFIED
8. Moderator submits to funder → SUBMITTED status
9. Organization reviews → APPROVED/REJECTED

### **Moderator Flow**
1. Register as Moderator (creates `ModeratorProfile`)
2. View dashboard with unassigned applications
3. Add scholarships to platform (optional)
4. Verify applications → Update `UploadedDocument` status
5. Assign moderator to applications
6. Log all actions → `ModeratorActivityLog`
7. Mark tasks complete

### **Organization/Funder Flow**
1. Register as Organization (creates `OrganizationProfile`)
2. Create scholarships → `Scholarship` records
3. Edit/manage own scholarships
4. Review applications from moderators
5. Approve/reject applications

### **AI Integration Flow** (Not yet implemented)
1. Eligibility Check: Match student profile against `EligibilityCriteria`
2. Document OCR: Verify uploaded documents
3. Log results in `AICheckLog`

---

## Key Issues & TODOs

### Critical Issues:
1. **Scholarship.organization field**: Uses CharField instead of ForeignKey
   - Should link to `OrganizationProfile`
   - Current code in `manage_scholarship()` tries to assign organization_profile object to string field
   
2. **Student dashboard not implemented**: `smart_dashboard_redirect()` redirects to non-existent view

3. **Moderator decorator commented out**: `@user_passes_test(is_moderator)` decorators are commented

4. **Media files not configured**: `upload_to='application_docs/'` requires MEDIA settings in settings.py

5. **External scholarships (source_url)**: System supports importing existing scholarships from external URLs

### Missing Features:
- AI integration API endpoints
- Eligibility matching algorithm
- Document OCR/validation
- Application review workflows
- Student portal views
- Scholarship search/filtering
- Dashboard statistics/analytics
- Error messages and success notifications
- CSRF protection on forms
- Email notifications
- User registration views (using Django admin)

### Commented Out Routes:
- `/scholarships/` - Scholarship listing
- `/applications/` - Application management
- `/api/ai/` - AI integration endpoints

---

## Database State

The project has `db.sqlite3` with migrations applied:
- **users**: 0001_initial.py, 0002_organizationprofile_user_is_organization.py
- **scholarships**: 0001_initial.py, 0002_rename_funder_scholarship_organization.py
- **applications**: 0001_initial.py, 0002_initial.py
- **moderator_panel**: 0001_initial.py, 0002_initial.py
- **ai_integrations**: (empty migrations dir)

This indicates the project has been developed incrementally with schema changes.

---

## Authentication & Access Control

**Login Required**: Protected views use `@login_required` decorator
**Role-Based Access**: Uses `@user_passes_test()` with custom checkers:
- `is_moderator(user)`: `user.is_moderator == True`
- `is_organization(user)`: `user.is_organization == True`

**Login Redirect Flow**:
1. User logs in at `/accounts/login/`
2. Redirects to `/accounts/dashboard/`
3. `smart_dashboard_redirect()` routes based on role flags

---

## Security Notes

**Current State:**
- DEBUG = True (development only)
- SECRET_KEY exposed in settings.py
- ALLOWED_HOSTS = [] (empty - should specify domains)
- No CSRF exemptions noted (good)

**Recommendations:**
- Move SECRET_KEY to environment variables
- Configure MEDIA_URL and MEDIA_ROOT for file uploads
- Add HTTPS/SSL in production
- Implement proper permission checks in views
- Validate file uploads by type and size

---

## Summary

Scholar Match is an in-development Django application for scholarship matching and management. The project has a solid data model foundation with clear separation of concerns (Students, Scholarships, Applications, Moderators, Organizations). 

**Current State**: Early-stage development with basic CRUD operations and role-based routing. Most features are scaffolded but not fully implemented (AI integration, student portal, application workflows).

**Next Steps**: Complete student portal views, implement eligibility matching algorithm, fix the Scholarship.organization field issue, and add comprehensive error handling and user notifications.
