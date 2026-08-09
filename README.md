# EventOps

A Django-based platform for managing corporate and institutional events end-to-end — from venue booking and vendor contracts to staff scheduling, budget tracking, and post-event reporting.

Built with a role-based access model (Admin / Event Manager / Finance Officer / Staff) so each team member only sees and does what their role allows.

---

## What it does

- **Events** — create, submit for approval, and track lifecycle from Draft through Completed
- **Venues** — maintain a venue registry with capacity, contact info, and availability status
- **Vendors** — contract vendors per event, log invoices and payment status
- **Staff & Scheduling** — assign staff to events with shift times and attendance check-in
- **Tasks** — per-event task lists with priority levels and completion tracking
- **Finance** — log expenses against event budgets; configurable warning thresholds (default: warn at 80%, critical at 90%)
- **Reports** — exportable summaries for events, finance, tasks, and vendor activity
- **Audit Log** — every significant action (create, update, delete) is timestamped and stored immutably
- **AI Analysis** — optional OpenRouter integration to get plain-English analysis of event performance and financial health
- **REST API** — full JWT-authenticated API with OpenAPI docs at `/api/schema/swagger-ui/`

---

## Tech stack

| Layer | Choice |
|---|---|
| Backend | Django 5.2 |
| API | Django REST Framework + drf-spectacular |
| Auth | Custom user model with role-based permissions |
| Database | PostgreSQL (SQLite for local dev) |
| Static files | WhiteNoise |
| Server | Gunicorn |

---

## Local setup

You need Python 3.11+ and PostgreSQL running locally (or use SQLite for quick testing).

**1. Clone and create a virtual environment**

```bash
git clone https://github.com/harsh23111157/event-management.git
cd event-management
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```

**2. Install dependencies**

```bash
pip install -r requirements.txt
```

**3. Configure environment**

```bash
cp .env.example .env
```

Edit `.env` — the minimum you need locally:

```
DEBUG=True
SECRET_KEY=any-random-string-here
ALLOWED_HOSTS=localhost,127.0.0.1
DATABASE_URL=sqlite:///db.sqlite3
```

**4. Run migrations and create a superuser**

```bash
python manage.py migrate
python manage.py createsuperuser
```

**5. Start the development server**

```bash
python manage.py runserver
```

Open [http://localhost:8000](http://localhost:8000) and log in with the superuser you created.

---

## Role permissions

| Action | Admin | Event Manager | Finance Officer | Staff |
|---|:---:|:---:|:---:|:---:|
| Create events | ✓ | ✓ | | |
| Approve events | ✓ | | | |
| Manage venues | ✓ | ✓ | | |
| Manage vendors | ✓ | ✓ | | |
| Assign staff | ✓ | ✓ | | |
| Log expenses | ✓ | ✓ | ✓ | ✓ |
| Approve expenses | ✓ | | ✓ | |
| View reports | ✓ | ✓ | ✓ | |
| Manage users | ✓ | | | |
| View audit log | ✓ | | | |

---

## Environment variables

| Variable | Required | Description |
|---|---|---|
| `SECRET_KEY` | Yes | Django secret key — use a long random string in production |
| `DEBUG` | Yes | `True` for development, `False` in production |
| `ALLOWED_HOSTS` | Yes | Comma-separated list of valid hostnames |
| `DATABASE_URL` | Yes | PostgreSQL URL or `sqlite:///db.sqlite3` for dev |
| `OPENROUTER_API_KEY` | No | Enables AI event analysis (get one free at openrouter.ai) |
| `OPENROUTER_MODEL` | No | Model slug, e.g. `nvidia/nemotron-3-ultra-550b-a55b:free` |

---

## Deploy to Railway

Railway is the easiest way to get this running in production with a free PostgreSQL database.

**Step 1 — Create a Railway project**

Go to [railway.app](https://railway.app), create a new project, and connect this GitHub repository.

**Step 2 — Add a PostgreSQL database**

In your Railway project, click **+ New** → **Database** → **PostgreSQL**. Railway will automatically set the `DATABASE_URL` environment variable.

**Step 3 — Set environment variables**

In Railway's service settings → Variables, add:

```
DJANGO_SETTINGS_MODULE=config.settings.production
SECRET_KEY=<generate a secure random key>
ALLOWED_HOSTS=<your-app>.up.railway.app
DEBUG=False
OPENROUTER_API_KEY=<optional>
OPENROUTER_MODEL=<optional>
```

Generate a secure key with:
```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

**Step 4 — Deploy**

Railway will detect the `Procfile` and build automatically. The `release` command runs `migrate` before each deploy so the database is always up to date.

After deploy, create your admin user via the Railway shell:
```bash
python manage.py createsuperuser
```

---

## API documentation

Once running, the auto-generated API docs are available at:

- Swagger UI: `/api/schema/swagger-ui/`
- ReDoc: `/api/schema/redoc/`
- OpenAPI JSON: `/api/schema/`

All endpoints require JWT authentication. Get a token at `/api/token/`.

---

## Running tests

```bash
pytest
```

Or with Django's test runner:

```bash
python manage.py test
```

The test suite covers accounts, events, venues, vendors, finance, operations, reports, audit, dashboard, and AI assistant — 26 tests total.

---

## Budget thresholds

The finance module tracks spending against event budgets and flags when limits are approached:

- **Warning** at 80% utilization — visible in the finance dashboard
- **Critical** at 90% — triggers a prominent alert on the event detail page

These thresholds are configurable in `config/settings/base.py`:

```python
BUDGET_WARN_THRESHOLD = 80
BUDGET_CRITICAL_THRESHOLD = 90
```

---

## Project structure

```
event-management/
├── apps/
│   ├── accounts/       # Custom user model, roles, permissions
│   ├── ai_assistant/   # OpenRouter integration and analysis
│   ├── audit/          # Immutable audit log
│   ├── dashboard/      # Dashboard views and context
│   ├── events/         # Event lifecycle management
│   ├── finance/        # Expense tracking and budget control
│   ├── operations/     # Staff, schedules, tasks, attendance
│   ├── reports/        # Reporting across all modules
│   ├── vendors/        # Vendor registry and event contracts
│   └── venues/         # Venue registry
├── config/
│   ├── settings/
│   │   ├── base.py         # Shared settings
│   │   ├── development.py  # Dev overrides
│   │   └── production.py   # Production hardening
│   ├── urls.py
│   └── wsgi.py
├── static/             # CSS, JS, fonts
├── templates/          # HTML templates (per-app)
├── Procfile            # Gunicorn start command
├── railway.toml        # Railway deployment config
├── requirements.txt
└── manage.py
```

---

## License

MIT
