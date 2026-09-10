# Student Management System (Flask)

A role-based Student Management System built with Flask, SQLAlchemy, Flask-Login,
Flask-WTF, and Bootstrap 5 — covering Admin, Teacher, Student, and Employee (HR)
workflows.

> ⚠️ **Upgrading from an older copy of this project?** New tables/columns were
> added (Department Microsite, Teacher Attendance, and earlier the Employee
> module). SQLite does not auto-migrate — **delete your existing `sms.db`**
> and run `init-db` + `seed-db` again, or you'll see "Internal Server Error"
> pages:
> ```bash
> rm sms.db            # Windows: Remove-Item sms.db
> python -m flask --app app.py init-db
> python -m flask --app app.py seed-db
> ```

## Quick Start

```bash
# 1. Create a virtual environment (recommended)
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Set the Flask app entrypoint
export FLASK_APP=app.py         # Windows (cmd): set FLASK_APP=app.py

# 4. Create the database tables
flask init-db

# 5. (Optional but recommended) Load demo data
flask seed-db

# 6. Run the development server
flask run
# or: python app.py
```

Visit **http://127.0.0.1:5000** in your browser.

> If `flask` isn't recognized on Windows PowerShell, use `python -m flask --app app.py <command>`
> instead of `flask <command>` for every step above.

## Demo Logins (after `flask seed-db`)

| Role     | Username       | Password      |
|----------|----------------|---------------|
| Admin    | `admin`        | `admin123`    |
| Teacher  | `anita.rao`    | `teacher123`  |
| Student  | `rahul.sharma` | `student123`  |
| Employee | `kavita.nair`  | `employee123` |

All accounts are created by the **admin only** — there is no public self-registration.
The admin sets Password + Confirm Password when adding a student, teacher, or employee.

In the demo data, **Dr. Anita Rao (anita.rao) is the HOD of Computer Science
Engineering** — log in as her to see the department microsite's admin/HOD-only
edit controls in action.

## What's Implemented

**Auth**
- Login only (no public registration) — animated glassmorphism sign-in page with
  remember me, show/hide password, and forgot/change password.
- Employee accounts log straight into their own self-service dashboard (see
  "Employee (self-service portal)" below).

**Admin**
- Dashboard: stat cards, department-wise and course-wise (UG/PG) student counts,
  fee stats, and Chart.js charts (student growth, attendance %, fee collection,
  course-wise students).
- Full CRUD + Edit for: Students, Teachers, Courses, Departments, Subjects, Notices.
- **Fee payment workflow**: students choose Cash or Online; the fee shows "Awaiting
  Confirmation" until the admin confirms receipt (works for College Fee, Exam Fee,
  and any custom fee type).
- **Auto-billing**: adding a student under a UG department (or a PG course) auto-creates
  their College Fee from that department's/course's fee amount. UG courses (B.E./B.Tech)
  are billed per-Department; PG courses (MBA/MCA, no departments) are billed directly.
- Department-wise Attendance Report with month filter + CSV export.
- **Department drill-down**: click a Department in Department Management to see
  Semesters 1–8 as clickable cards (with live student counts); click a semester
  to see its student list, with an "Add Student" button that pre-fills the
  department and semester on the add-student form.
- **Course drill-down**: click a Course in Course Management. UG courses
  (B.E./B.Tech, which have departments) open the list of Departments under
  that course. PG courses (MBA/MCA, no departments) open semester cards
  directly — sized to the course's duration (e.g. a 2-year course shows
  Semesters 1–4) — with the same "Add Student" pre-fill behavior.
- **Teacher Attendance is view-only for admin**: teachers mark their own daily
  attendance from their portal (see Teacher section below); admin only sees a
  read-only report + monthly CSV export. All three attendance types (Student,
  Teacher, Employee) are grouped under one **Attendance** dropdown in the nav.
- **Clickable names everywhere**: student, teacher, and employee names are
  links to their detail pages across every list (admin's Students/Teachers/
  Employees, the Department/Course drill-down pages, and the Teacher's own
  Student List). A Teacher detail view (profile + self-reported attendance
  history) and a teacher-scoped Student detail view (marks + attendance,
  read-only) were added to support this.
- Examination Module (course → subject → hall/date/time), Timetable Management
  (weekly per-department), Event Management (College Events/Workshops/Seminars/Sports).
- Library Module: books, issue/return with automatic ₹5/day late fine.
- Transport Module: buses/routes/drivers, visible read-only to students & teachers.
- Leave Requests: Approve/Reject.
- Reports hub: CSV export for Student/Attendance/Fee/Marks/Assignment reports.
- **Employee / HR Module**: dashboard (total/present-today/on-leave/new employees,
  department breakdown, salary summary, announcements); Add/Edit/Delete/View employees
  with Search + Filter by Department/Designation + Print view; daily attendance
  (Present/Absent/Half Day/Leave + check-in/out) with report + export; leave
  requests (record/approve/reject/cancel); CSV export. Designations cover Principal,
  Vice Principal, HOD, Librarian, Accountant, Office Staff, Lab Assistant, Receptionist,
  Hostel Warden, Transport Manager, Bus Driver, Security Guard, Cleaner/Housekeeping,
  IT Administrator, Placement Officer, Sports Coach, and Nurse/Medical Staff.
  (Teaching staff continue to be managed via Teacher Management.)

**Employee (self-service portal)**
- Employees log in to their own dashboard: attendance %, pending leave count,
  designation/department, upcoming approved leave, and announcements.
- Profile: view personal/contact/qualification/experience details, edit phone
  and address, update profile photo. Salary is intentionally **not shown**
  here — it's admin-only, as specified.
- Attendance: view their own full attendance history + overall percentage.
- Leave: apply for leave, view status, and cancel while still Pending.

**Department Microsite** (`/departments`, visible to every logged-in role)
- Click any department (from Course Management, Department Management, or the
  universal **Departments** nav link) to open one full profile page covering:
  Overview, History, Head of Department, Technical Faculty (click a name for
  their full profile — qualification, research areas, publications,
  certifications, projects, awards, office hours), Non-Technical Staff,
  Laboratories, Courses Offered (by semester, with syllabus PDF + course
  outcomes), Students (by semester), Achievements, Placements (stats +
  individual records), Events, Notices, Downloads, a weekly Timetable, and
  Contact (info + a working contact form).
- **View access**: everyone logged in (Admin, Teacher, Student, Employee).
- **Edit access**: only the **Admin** or that department's own **HOD**
  (a teacher whose designation is "HOD" and whose department matches) can add/
  edit any section — labs, achievements, placements, events, notices,
  documents, timetable, overview/history text, and the HOD's own cabin/
  message. This is enforced server-side (not just hidden buttons) — verified
  by testing that a non-HOD teacher, student, or employee gets a 403 if they
  try to hit an edit URL directly.
- Faculty and Staff rosters themselves are still added via Teacher Management
  and Employee Management (personnel records stay with admin); the extra
  faculty-profile fields (research areas, publications, etc.) are edited from
  the Teacher edit form.

**Teacher**
- Dashboard, Student List (+ CSV export, click a name for their detail/marks/
  attendance), take/view student attendance, upload assignments + review
  submissions, enter marks (auto grade/pass-fail), upload Study Materials,
  view department Timetable & Notices & Transport routes, Reports hub.
- **My Attendance**: teachers mark their own daily attendance (Present/Absent/
  Half Day/Leave + check-in/out) and view their own history — admin cannot
  mark it for them, only view/export it (see Admin section above).

**Student**
- Dashboard, profile view/edit, attendance %, view/submit assignments, results +
  **Marksheet PDF download**, Fees (with Pay Now → Cash/Online flow), Timetable,
  Notices, Study Materials, Transport (shows assigned bus), Leave requests
  (submit + **edit while pending**).

**Cross-cutting**
- Dark mode toggle, role-based access control, Bootstrap 5 UI with a custom
  navy/gold theme.
- **Themed background images**: the login page and each portal (Admin/Teacher/
  Student/Employee dashboards — applied site-wide per role, not just the landing
  page) show a full-bleed background image with a dark readability overlay.
  Placeholder abstract images matching the app's navy/gold/teal palette are
  included so it works out of the box. **To use your own photos**, just replace
  the files at `static/images/backgrounds/` (same filenames, any resolution —
  they're displayed as `cover`):
  - `login-bg.jpg` — sign-in page
  - `admin-bg.jpg` — Admin portal
  - `teacher-bg.jpg` — Teacher portal
  - `student-bg.jpg` — Student portal
  - `employee-bg.jpg` — Employee holding page

## Database Schema

See `models.py` for the full schema: Users, Students, Teachers, Employees,
Employee Attendance, Employee Leave Requests, Teacher Attendance, Courses,
Departments, Classes, Subjects, Attendance, Assignments, Assignment
Submissions, Study Materials, Exams, Marks, Fees, Payments, Timetables,
Notices, Events, Leave Requests, Books, Book Issues, Buses, Laboratories,
Department Achievements, Placement Records, Department Documents, and
Department Contact Messages.

## Not Yet Wired Up (left as clear extension points)

- **Photo galleries** for departments and labs (the microsite covers every
  text/data section from the spec; image galleries would need a multi-upload
  UI, which is a reasonable next addition on top of the existing single-photo
  upload pattern already used elsewhere).
- **Class Representative assignment** and full per-student
  Achievements/Internships/Projects tracking (department-level Achievements
  and Placements are implemented; per-student versions would reuse the same
  pattern).
- **Documents module** (Aadhaar/PAN/Certificates upload per employee).
- **Hostel Management**, **Activity Logs**, **Notifications module**, and a
  dedicated **Settings & Profile** page.
- **PDF/Excel report generation** beyond the Student Marksheet PDF — the CSV
  reports open natively in Excel; a full ReportLab/OpenPyXL pass over every
  report type follows the same pattern as the marksheet PDF.
- **Employee self-service portal** currently covers dashboard/profile/
  attendance/leave; a documents section and richer notifications could be
  layered on later.

## Project Structure

```
sms/
├── app.py                 # App factory, CLI commands (init-db, seed-db)
├── config.py               # Configuration (secret key, DB URI, uploads)
├── extensions.py            # db, login_manager singletons
├── models.py                 # All SQLAlchemy models
├── forms.py                   # Flask-WTF forms (login, forgot password)
├── utils.py                    # File upload helpers, role/HOD permission guards, date parsing
├── seed.py                      # Demo data loader
├── requirements.txt
├── blueprints/
│   ├── auth/        # login, logout, forgot/change password
│   ├── admin/        # dashboard + all management CRUD + Employee/HR module
│   ├── teacher/       # dashboard, attendance, assignments, marks, materials...
│   ├── student/        # dashboard, profile, attendance, assignments, results, fees...
│   ├── employee/        # self-service dashboard, profile, attendance, leave
│   └── department/       # department microsite (view: all roles; edit: admin/HOD only)
├── templates/
│   ├── base.html, auth/, admin/, teacher/, student/, employee/, department/, errors/
└── static/
    ├── css/style.css
    ├── js/main.js
    ├── images/backgrounds/   # login-bg.jpg, admin-bg.jpg, teacher-bg.jpg, student-bg.jpg, employee-bg.jpg
    └── uploads/              # profile photos, driver photos, assignment/material/syllabus PDFs
```

## Notes

- Default database is SQLite (`sms.db`). Set `DATABASE_URL` to point at MySQL/Postgres
  in production.
- Uploaded files are capped at 5 MB; images: png/jpg/jpeg/gif, documents: pdf.
- Change `SECRET_KEY` via the `SECRET_KEY` environment variable before deploying.
