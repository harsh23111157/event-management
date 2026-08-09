# EventOps — Enterprise Event Operations Platform

[![Live Deployment](https://img.shields.io/badge/Railway-Live%20Demo-6366f1?style=flat-square&logo=railway)](https://web-production-2c66.up.railway.app)
[![Django](https://img.shields.io/badge/Django-5.2-092E20?style=flat-square&logo=django)](https://djangoproject.com)
[![Python](https://img.shields.io/badge/Python-3.13-3776AB?style=flat-square&logo=python)](https://python.org)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Ready-4169E1?style=flat-square&logo=postgresql)](https://postgresql.org)
[![Tests](https://img.shields.io/badge/Tests-26%20Passed-22c55e?style=flat-square)](https://github.com/harsh23111157/event-management)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=flat-square)](https://opensource.org/licenses/MIT)

**EventOps** is a production-ready enterprise platform for managing corporate and institutional events end-to-end — from venue procurement and vendor contracts to staff dispatching, budget control, automated multi-factor AI risk scoring, and post-event reconciliation.

🌐 **Live Production Application:** [https://web-production-2c66.up.railway.app](https://web-production-2c66.up.railway.app)  
📄 **Interactive Visual Showcase:** Open [`README.html`](./README.html) in your browser for a dark-mode, animated platform walkthrough.

---

## Core Capabilities

- **Event Lifecycle Orchestration:** Full workflow states (`Draft` &rarr; `Submitted` &rarr; `Approved` &rarr; `In Progress` &rarr; `Completed` &rarr; `Rejected`/`Cancelled`) with strict role-based transitions and rejection audit logs.
- **Automated AI Event Health Engine:** Instant deterministic 0–100 scoring per event calculated across 6 operational dimensions (budget utilization, task velocity, staff coverage, vendor confirmations, time buffer, and approval state).
- **AI Executive Morning Briefing:** On-demand portfolio synthesis delivering plain-English risk assessments and prioritized action items via OpenRouter LLM or built-in deterministic fallback.
- **Financial Governance & Threshold Alerts:** Budget allocation, line-item expense approvals, configurable warning alerts (80% warning / 90% critical utilization), and category analytics.
- **Venue & Vendor Registry:** Capacity enforcement vs. attendee counts, availability tracking, vendor contracting, and invoice reconciliation.
- **Staff Operations & Digital Check-In:** Shift scheduling, task assignment with priority levels, and timestamped attendance tracking.
- **Role-Based Access Control (RBAC):** Granular permission isolation for 4 roles: `Admin`, `Event Manager`, `Finance Officer`, and `Staff Member`.
- **Immutable Audit Trail:** Automatic capture of actor, action, timestamp, IP address, and change diff for compliance and accountability.
- **RESTful API & OpenAPI Schema:** JWT-authenticated endpoints powered by Django REST Framework with auto-generated Swagger UI at `/api/schema/swagger-ui/`.

---

## System Architecture

```
                                  ┌──────────────────────────────┐
                                  │      Cloudflare / Proxy      │
                                  └──────────────┬───────────────┘
                                                 │ HTTPS
                                  ┌──────────────▼───────────────┐
                                  │        Gunicorn WSGI         │
                                  │    (/health/ bypass layer)   │
                                  └──────────────┬───────────────┘
                                                 │
                  ┌──────────────────────────────┼──────────────────────────────┐
                  │                              │                              │
        ┌─────────▼─────────┐          ┌─────────▼─────────┐          ┌─────────▼─────────┐
        │  Server-Rendered  │          │   REST API Layer  │          │   AI Intelligence │
        │   HTML + DTL UI   │          │ (DRF + JWT Auth)  │          │ (Health + LLM)   │
        └─────────┬─────────┘          └─────────┬─────────┘          └─────────┬─────────┘
                  │                              │                              │
                  └──────────────────────────────┼──────────────────────────────┘
                                                 │
                                  ┌──────────────▼───────────────┐
                                  │   PostgreSQL / SQLite ORM    │
                                  │   (Events, Audit, Ops, Fin)  │
                                  └──────────────────────────────┘
```

---

## Role-Based Access Control Matrix

| Operational Capability | 👑 Admin | 🎯 Event Manager | 💳 Finance Officer | 👷 Staff Member |
|---|:---:|:---:|:---:|:---:|
| Create & Edit Events | ✅ | ✅ (Assigned) | ❌ | ❌ |
| Approve / Reject Events | ✅ | ❌ | ❌ | ❌ |
| Manage Venues & Capacity | ✅ | ✅ | ❌ | ❌ |
| Vendor Procurement & Links | ✅ | ✅ | ❌ | ❌ |
| Staff Shift Scheduling | ✅ | ✅ | ❌ | ❌ |
| Submit Expense Requests | ✅ | ✅ | ✅ | ✅ |
| Approve / Reject Expenses | ✅ | ❌ | ✅ | ❌ |
| View Financial Reports | ✅ | ✅ (Own) | ✅ (Full) | ❌ |
| View Immutable Audit Logs | ✅ | ❌ | ❌ | ❌ |
| User & Role Administration | ✅ | ❌ | ❌ | ❌ |
| Real-Time AI Briefing & Scores | ✅ | ✅ (Own) | ✅ | ❌ |

---

## Automated AI Event Health Engine

The AI Health Engine continuously evaluates each event on a 0–100 scale using deterministic weights, providing instant feedback without API latency:

```
Total Health Score = State (20pts) + Budget (25pts) + Tasks (20pts) + Staff (15pts) + Vendors (10pts) + Time (10pts)
```

- **Grade A (80–100):** Healthy — All parameters on track.
- **Grade B (65–79):** Moderate — Minor task or vendor follow-ups needed.
- **Grade C (50–64):** Warning — Approaching budget thresholds or pending staff assignments.
- **Grade D/F (<50):** Critical Risk — Immediate intervention required.

---

## Production Verification & QA Results

A comprehensive test suite was executed against both local unit test runners and the live Railway production instance:

```bash
# Unit test run
pytest
# Ran 26 tests in 38.4s — 100% Passing
```

| Test Case | Description | Target / Route | Result |
|---|---|---|---|
| `TC-01` | WSGI Healthcheck Endpoint | `GET /health/` | ✅ **PASS** (200 OK) |
| `TC-02` | Static Assets & Styling | `/static/css/styles.css` | ✅ **PASS** (WhiteNoise) |
| `TC-03` | Authentication Guard | Unauth redirect to `/login/` | ✅ **PASS** (302 Redirect) |
| `TC-04` | CSRF Token Generation | Form verification | ✅ **PASS** (Token Valid) |
| `TC-05` | Admin Authentication | `admin / admin12345` | ✅ **PASS** (Dashboard 200) |
| `TC-06` | Event Lifecycle Transition | Draft &rarr; Submitted &rarr; Approved | ✅ **PASS** (State Machine) |
| `TC-07` | Venue Contact Email Schema | `apps/venues/models.py` | ✅ **PASS** (Field Present) |
| `TC-08` | Budget Threshold Warnings | Utilization >= 80% / 90% | ✅ **PASS** (Alerts Render) |
| `TC-09` | Staff Attendance Check-In | Timestamped shift tracking | ✅ **PASS** (Record Logged) |
| `TC-10` | Role-Based Access Isolation | Staff accessing `/audit-logs/` | ✅ **PASS** (403 Forbidden) |
| `TC-11` | Automated AI Health Scoring | Multi-factor calculation | ✅ **PASS** (Computed Live) |
| `TC-12` | AI Portfolio Briefing API | `GET /dashboard/ai-briefing/` | ✅ **PASS** (JSON Delivered) |
| `TC-13` | Interactive Workflow Guide | `GET /workflow/` | ✅ **PASS** (Guide Rendered) |
| `TC-14` | REST API OpenAPI Swagger UI | `GET /api/schema/swagger-ui/` | ✅ **PASS** (Interactive Docs) |
| `TC-15` | Database Auto-Seed on Deploy | `start.sh` migration hook | ✅ **PASS** (Zero Downtime) |

---

## Quickstart & Local Setup

### Prerequisites
- Python 3.11+ (Python 3.13 recommended)
- PostgreSQL (or SQLite for local development)
- Git

### 1. Clone & Environment Setup
```bash
git clone https://github.com/harsh23111157/event-management.git
cd event-management
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure Environment Variables
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```

Set the following local settings:
```ini
DEBUG=True
SECRET_KEY=local-insecure-secret-key-for-development
ALLOWED_HOSTS=localhost,127.0.0.1
DATABASE_URL=sqlite:///db.sqlite3
# Optional: OpenRouter API Key for enhanced LLM analysis
OPENROUTER_API_KEY=
OPENROUTER_MODEL=openrouter/auto
```

### 3. Initialize Database & Seed Demo Data
```bash
python manage.py migrate
python manage.py seed_demo_data
```

### 4. Run Development Server
```bash
python manage.py runserver
```
Visit [http://localhost:8000](http://localhost:8000) and log in with any of the seeded credentials:

| Role | Username | Password |
|---|---|---|
| **Admin** | `admin` | `admin12345` |
| **Event Manager** | `manager` | `manager12345` |
| **Finance Officer** | `finance` | `finance12345` |
| **Staff Member** | `staff` | `staff12345` |

---

## REST API Reference

The API is fully documented via OpenAPI 3.0 / Swagger at `/api/schema/swagger-ui/`.

### Authentication
Obtain a JSON Web Token pair:
```bash
curl -X POST https://web-production-2c66.up.railway.app/api/token/ \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "admin12345"}'
```

### Key API Endpoints
- `GET /api/events/` — List all accessible events with pagination & filters
- `POST /api/events/` — Create new event (Managers & Admins)
- `GET /api/events/{id}/` — Retrieve detailed event metrics and health factors
- `GET /api/venues/` — Venue registry and capacity index
- `GET /api/vendors/` — Vendor database and linked event contracts
- `GET /api/expenses/` — Line-item expense registry and approval status
- `POST /api/expenses/` — Submit new expense with receipt attachments
- `POST /api/operations/attendance/` — Record staff check-in / check-out
- `GET /dashboard/ai-briefing/` — Fetch real-time AI executive portfolio briefing

---

## Deployment Guide (Railway / Cloud)

This codebase is pre-configured with a zero-friction production setup via `start.sh`, `railway.toml`, and `Procfile`.

### Environment Configuration in Railway:
1. Connect GitHub repository to **Railway**.
2. Provision a **PostgreSQL** database addon (Railway sets `DATABASE_URL` automatically).
3. Set the following environment variables:
   ```ini
   DJANGO_SETTINGS_MODULE=config.settings.production
   SECRET_KEY=<your-cryptographically-secure-secret-key>
   DEBUG=False
   ```
4. Deploy! `start.sh` automatically performs:
   - `python manage.py migrate`
   - `python manage.py seed_demo_data`
   - `python manage.py collectstatic --noinput`
   - Starts Gunicorn with optimized worker concurrency.

---

## Repository Structure

```
event-management/
├── apps/
│   ├── accounts/       # User models, custom RBAC permissions, role auth
│   ├── ai_assistant/   # OpenRouter LLM service & prompt templates
│   ├── audit/          # Immutable change tracking & audit logs
│   ├── dashboard/      # Role-specific analytics, KPI services, charts
│   ├── events/         # Event state machine & AI health scoring engine
│   ├── finance/        # Expense tracking, approvals, budget thresholds
│   ├── operations/     # Staff scheduling, task Kanban, attendance
│   ├── reports/        # PDF/CSV reporting and analytics
│   ├── vendors/        # Vendor registry & contract management
│   └── venues/         # Venue catalogue & capacity enforcement
├── config/             # Django root configuration & settings
├── static/             # CSS styling, Chart.js modules, assets
├── templates/          # Semantic HTML5 templates & component partials
├── README.html         # Interactive visual platform showcase
├── README.md           # Engineering & deployment documentation
├── start.sh            # Production entrypoint script
├── railway.toml        # Railway platform specification
└── manage.py           # Django CLI entrypoint
```

---

## License

This project is licensed under the MIT License. See [`LICENSE`](./LICENSE) for full details.
