# Campus Student Support and Concern Portal

A web application built for university student support and grievance lifecycle management. Designed to address student discovery insights: eliminating ambiguity over whom to approach, avoiding wasted trips to empty staff cabins, providing transparent progress timelines, enforcing strict confidentiality for wellbeing concerns, preventing duplication with the campus facilities maintenance portal, and giving university staff a structured priority queue.

---

## Architecture and Key Highlights

- **Framework**: Python 3.14+ with Flask (App Factory pattern & Blueprints).
- **Database & ORM**: SQLite with Flask-SQLAlchemy.
- **Authentication & RBAC**: Flask-Login with password hashing (`scrypt`/`pbkdf2`), server-side role-based access decorators (`@student_required`, `@staff_required`, `@admin_required`, `@wellbeing_required`).
- **Database-Driven Routing**: Concerns are auto-routed using a database routing table (`RoutingRule`) completely editable by Admin—no hardcoded routing assumptions.
- **Strict Wellbeing Confidentiality**: Wellbeing concerns are visible **strictly and exclusively** to the student who raised them and authorized `Wellbeing/Health Staff`. They are hidden from other staff, general queues, and excluded from administrator content counts.
- **Configurable Escalation & Overdue SLA**: Staff can escalate unresolvable concerns along configurable escalation chains (`EscalationRule`). Concerns unacknowledged past the configurable threshold (default: 24h) are flagged as `OVERDUE`.
- **Cabin Hours & Appointments**: Staff publish availability slots with cabin locations. Students book slots directly or submit ad-hoc requests; staff approve, decline, or reschedule.
- **Non-Duplication of Maintenance**: Maintenance and housekeeping concerns are directed to the campus facilities portal via a configurable external link rather than duplicating tickets.
- **In-App Notifications**: Real-time notifications for status transitions, comments, and appointment bookings.

---

## User Roles and Demo Credentials

All demo accounts are pre-seeded in `seed.py` with the standard password: **`Password123!`**

| Role | Name | Email | Primary Responsibilities |
| :--- | :--- | :--- | :--- |
| **Student** | Alex Rivera | `student@campus.edu` | Raises and tracks concerns, books appointments |
| **Student (Isolated)** | Jordan Lee | `student2@campus.edu` | Used for verifying cross-student privacy isolation |
| **Mentor** | Dr. Sarah Vance | `mentor@campus.edu` | Academic concerns, elective clashes, advising |
| **Program Coordinator** | Prof. Alan Turing | `coordinator@campus.edu` | Examination results, grading, syllabus |
| **Warden** | Col. James Wilson | `warden@campus.edu` | Mess food quality, dining hygiene, hostel issues |
| **Head Warden** | Prof. Marcus Brody | `headwarden@campus.edu` | Disciplinary escalations across hostels |
| **Dean of Student Affairs**| Dean Robert Hayes | `dean_sa@campus.edu` | Senior student grievance escalations |
| **Dean** | Dean Eleanor Roosevelt| `dean@campus.edu` | Final university executive escalation level |
| **Wellbeing/Health Staff**| Dr. Grace Hopper | `wellbeing@campus.edu` | **Confidential** mental health & counseling |
| **Administrator** | System Administrator | `admin@campus.edu` | Users, dynamic routing table, escalations, SLAs |

---

## Directory Structure

```text
campus_concern_portal/
├── .env.example              # Sample environment variables
├── README.md                 # Complete system guide
├── requirements.txt          # Python dependencies
├── run.py                    # Entry point for running the application
├── seed.py                   # Demo database seeder script
├── pytest.ini                # Pytest configuration
├── app/
│   ├── __init__.py           # Application Factory, filters, and error handlers
│   ├── config.py             # Config classes (Dev, Test, Prod)
│   ├── extensions.py         # SQLAlchemy, LoginManager, CSRFProtect
│   ├── forms.py              # Flask-WTF validation forms
│   ├── models/
│   │   ├── __init__.py       # Model exports
│   │   ├── user.py           # User and Role definitions
│   │   ├── concern.py        # Concern, Category, Urgency, Timeline, Comment
│   │   ├── appointment.py    # AvailabilitySlot, Appointment, Status
│   │   ├── routing.py        # RoutingRule, EscalationRule, SystemSetting
│   │   └── notification.py   # In-app Notification model
│   ├── services/
│   │   ├── __init__.py       # Service exports
│   │   ├── concern_service.py     # Routing, triage, escalation, privacy logic
│   │   ├── appointment_service.py # Slots, booking, reschedule workflow
│   │   └── notification_service.py# In-app notifications
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── decorators.py     # RBAC security decorators
│   │   └── helpers.py        # Unique tracking numbers, date filters
│   ├── blueprints/
│   │   ├── auth/             # Login, register, logout
│   │   ├── student/          # Dashboard, concern submission, appointments
│   │   ├── staff/            # Queue, triage, availability, appointments
│   │   ├── admin/            # Rules, escalations, users, settings
│   │   └── main/             # Landing, directory, maintenance link, notifications
│   ├── static/
│   │   ├── css/style.css     # Responsive design, status badges, progress steppers
│   │   └── js/main.js        # Client-side dynamic alerts & interactive helpers
│   └── templates/
│       ├── base.html         # Navbar, flash messages, footer layout
│       ├── error.html        # 403, 404, 500 error views
│       ├── index.html        # Landing page with 1-click demo logins
│       ├── directory.html    # "Who do I contact?" interactive directory
│       ├── maintenance.html  # External facilities portal redirect
│       ├── notifications.html# In-app notification center
│       ├── auth/             # Sign in & registration templates
│       ├── student/          # Student dashboard & concern details
│       ├── staff/            # Staff priority queue, triage & slots
│       └── admin/            # Admin dashboard, routing & escalation tables
└── tests/
    ├── conftest.py           # Test fixtures, in-memory SQLite, user loggers
    ├── test_auth.py          # Registration, login, active checks, RBAC
    ├── test_routing.py       # DB routing, admin updates, maintenance block
    ├── test_status_and_comments.py # Lifecycles, comments, audit trails
    ├── test_escalation.py    # Escalation chains, overdue SLA, queue sorting
    ├── test_appointments.py  # Slot publishing, requests, declines, reschedules
    └── test_wellbeing_confidentiality.py # Strict isolation & privacy proofs
```

---

## Setup and Installation

### 1. Prerequisites
- Python 3.10+ (tested on Python 3.14)
- Git and virtualenv

### 2. Create Virtual Environment and Install Dependencies
```bash
# Navigate to the project root
cd campus_concern_portal

# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Initialize and Seed Demo Data
```bash
python seed.py
```
This initializes the SQLite database with all demo roles, dynamic routing rules, escalation chains, published cabin slots, and realistic sample concerns.

### 4. Run the Development Server
```bash
export FLASK_APP=run.py
export FLASK_ENV=development
flask run
```
Or simply:
```bash
python run.py
```
Open **[http://127.0.0.1:5000](http://127.0.0.1:5000)** in your browser.

---

## Running Automated Tests

Run the complete pytest test suite covering authentication, database routing, status lifecycles, escalation chains, appointment scheduling, and wellbeing confidentiality:

```bash
pytest -v
```

All 21 test scenarios execute in an isolated in-memory test database and verify:
1. `test_auth.py`: Student registration, password hashing, role enforcement, and 403 authorization barriers.
2. `test_routing.py`: Auto-routing using database routing table, admin real-time route updates, and blocking of maintenance concerns.
3. `test_status_and_comments.py`: Full status lifecycle (Submitted &rarr; Acknowledged &rarr; In Progress &rarr; Resolved &rarr; Closed), timestamp tracking, and bi-directional comments.
4. `test_escalation.py`: Chain progression across roles, mandatory escalation reasons, overdue SLA flagging, and priority sorting by urgency & age.
5. `test_appointments.py`: Publishing cabin slots, student booking, approval, decline slot-reopening, and rescheduling.
6. `test_wellbeing_confidentiality.py`: Server-side isolation proving Mentors, Wardens, Deans, Admins, and other students cannot view wellbeing concerns, that non-wellbeing staff queues exclude them, and that admin analytics preserve student privacy.
