# Business Automation Agent

[![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-4169E1?logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![Redis](https://img.shields.io/badge/Redis-7-DC382D?logo=redis&logoColor=white)](https://redis.io/)
[![Celery](https://img.shields.io/badge/Celery-5.4+-37814A?logo=celery&logoColor=white)](https://docs.celeryq.dev/)
[![Gemini](https://img.shields.io/badge/Google_Gemini-API-4285F4?logo=google&logoColor=white)](https://ai.google.dev/)
[![Stripe](https://img.shields.io/badge/Stripe-Webhooks-635BFF?logo=stripe&logoColor=white)](https://stripe.com/)
[![Resend](https://img.shields.io/badge/Resend-Email-000000?logo=resend&logoColor=white)](https://resend.com/)
[![Amazon S3](https://img.shields.io/badge/Amazon_S3-Storage-569A31?logo=amazons3&logoColor=white)](https://aws.amazon.com/s3/)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker&logoColor=white)](https://docs.docker.com/compose/)
[![pytest](https://img.shields.io/badge/pytest-8.3+-0A9EDC?logo=pytest&logoColor=white)](https://docs.pytest.org/)
[![Ruff](https://img.shields.io/badge/Ruff-Lint-D7FF64?logo=ruff&logoColor=black)](https://docs.astral.sh/ruff/)
[![Deploy on Render](https://img.shields.io/badge/Deploy-Render-46E3B7?logo=render&logoColor=white)](https://render.com/docs/deploy-fastapi)
[![CI](https://img.shields.io/badge/CI-GitHub_Actions-2088FF?logo=githubactions&logoColor=white)](.github/workflows/ci.yml)

Event-driven backend that ingests business events (primarily Stripe webhooks), analyzes them with deterministic rules and Gemini, persists decisions, and executes automated actions: PDF generation, S3 upload, and email delivery.

---

## Table of contents

| Section | Topic |
|---|---|
| [Overview](#overview) | What the system does and how it differs from rule-only automation |
| [Architecture](#architecture) | Pipeline, components, and diagrams |
| [Technical reference](#technical-reference) | Event lifecycle, data model, security, and failure semantics |
| [Tech stack](#tech-stack) | Versions and roles |
| [Getting started](#getting-started) | Prerequisites, local setup, env vars, tests |
| [API reference](#api-reference) | Endpoints and auth model |
| [Operations](#operations) | CI, Render deployment, project layout |

---

## Overview

### What it does

**Business Automation Agent** is an operational automation platform built around an event pipeline. External systems send signals (for example, a failed Stripe payment). The platform stores each signal as an **Event**, processes it asynchronously, produces a structured **Decision**, and runs one or more **Actions** (report, email, notification).

### Rule engine + AI

Unlike a traditional rule-only automation stack, this system combines:

| Layer | Role |
|---|---|
| **Rule Engine** | Deterministic priority and `rule_triggered` before calling Gemini |
| **Gemini** | Contextual `classification`, `summary`, and `recommendations` JSON |
| **Action Executor** | Side effects (PDF, S3, Resend) driven by recommendation keys |

The Rule Engine sets guardrails (e.g. `payment_failed` → `high` priority). Gemini fills in narrative context and action keys (`send_email`, `generate_report`, `notify_team`). The executor maps those keys to concrete integrations.

---

## Architecture

### Main flow

```text
Stripe Webhook
      │
      ▼
  FastAPI (ingest + validate signature)
      │
      ▼
  Event (PostgreSQL, status: pending)
      │
      ▼
  Celery task (Redis broker)
      │
      ▼
  EventProcessor
      │
      ├──► BusinessAgent
      │         ├── RuleEngine   (priority, rule_triggered)
      │         └── GeminiClient (summary, recommendations)
      │
      ▼
  Decision (PostgreSQL)
      │
      ▼
  ActionExecutor
      ├── report        → ReportService → PDF + S3
      ├── email         → EmailService → Resend
      └── notification  → simulated internal alert
```

```mermaid
flowchart TB
    subgraph ingest["Ingestion (sync)"]
        WH[Stripe Webhook] --> API[FastAPI]
        API --> EV[(events)]
    end

    subgraph async["Processing (async)"]
        EV --> Q[Redis / Celery]
        Q --> WP[Celery Worker]
        WP --> EP[EventProcessor]
        EP --> BA[BusinessAgent]
        BA --> RE[RuleEngine]
        BA --> GM[Gemini API]
        EP --> DEC[(decisions)]
        EP --> AE[ActionExecutor]
    end

    subgraph sidefx["Side effects"]
        AE --> PDF[ReportLab PDF]
        PDF --> S3[(Amazon S3)]
        AE --> RS[Resend Email]
    end
```

### Layered design

```text
┌─────────────────────────────────────────────────────────┐
│  API Layer          app/api/routes/ + dependencies      │
├─────────────────────────────────────────────────────────┤
│  Services           event, auth, report, email, action  │
├─────────────────────────────────────────────────────────┤
│  Agents / Rules     BusinessAgent, RuleEngine           │
├─────────────────────────────────────────────────────────┤
│  Integrations       S3, Resend, Stripe (webhook verify) │
├─────────────────────────────────────────────────────────┤
│  Repositories       SQLAlchemy data access              │
├─────────────────────────────────────────────────────────┤
│  Infrastructure     PostgreSQL, Redis, Celery           │
└─────────────────────────────────────────────────────────┘
```

### Components

| Component | Location | Responsibility |
|---|---|---|
| **API routes** | `app/api/routes/` | HTTP layer, auth, webhook ingestion |
| **EventService** | `app/services/event_service.py` | Event creation, Stripe idempotency, Celery enqueue |
| **EventProcessor** | `app/services/event_processor.py` | Orchestrates pipeline in an atomic DB transaction |
| **BusinessAgent** | `app/agents/business_agent.py` | Combines RuleEngine + Gemini into a decision payload |
| **RuleEngine** | `app/rules/rule_engine.py` | Deterministic rules by `event_type` |
| **GeminiClient** | `app/decision_engine/gemini_client.py` | Prompting and parsing Gemini JSON responses |
| **ActionExecutor** | `app/action_executor/action_executor.py` | Maps recommendations to actions and executes them |
| **ReportService** | `app/services/report_service.py` | PDF generation and S3 upload |
| **EmailService** | `app/services/email_service.py` | HTML email via Resend |
| **Celery** | `app/tasks/` | Async processing (`process_event_task`) |

---

## Technical reference

Dense implementation notes for developers operating or extending the system.

### Event lifecycle

| Status | Set by | Meaning |
|---|---|---|
| `received` | `EventService.create_event` | Manual event ingested via API (not enqueued to Celery) |
| `pending` | `EventService.ingest_stripe_webhook` | Stripe event stored; Celery task scheduled |
| `processing` | `EventProcessor.process` | Worker started pipeline |
| `completed` | `EventProcessor.process` | Decision + actions committed successfully |
| `failed` | `EventProcessor.process` | Pipeline raised; status persisted in separate transaction |

```text
Stripe webhook:  pending → processing → completed | failed
Manual POST:     received  (no automatic Celery enqueue today)
```

### Data model (core entities)

| Table | Key fields | Relationships |
|---|---|---|
| `events` | `event_type`, `source`, `payload` (JSONB), `status`, `stripe_event_id` (UNIQUE) | 1:1 `decisions`, 1:N `actions`, 0:1 `reports` |
| `decisions` | `priority`, `classification`, `summary`, `recommendations` (JSONB), `rule_triggered` | FK → `events.id` |
| `actions` | `action_type`, `status`, `result` (JSONB), `executed_at` | FK → `events.id`, `decisions.id` |
| `reports` | `type`, `s3_url` | FK → `events.id`, `decisions.id`; UNIQUE on `decision_id` |
| `users` | `email`, `hashed_password`, `role`, `active` | JWT auth |

Indexes on `events`: `created_at`, `status`, `event_type`, `customer_id`.

### Stripe idempotency

1. **Pre-insert check** — `get_event_by_stripe_event_id()` returns `already_processed` (HTTP 200).
2. **Concurrent duplicates** — `IntegrityError` on UNIQUE `stripe_event_id` is caught, rolled back, and resolved to `already_processed`.
3. **Webhook security** — raw body verified with `stripe.Webhook.construct_event()` and `STRIPE_WEBHOOK_SECRET`.

### Pipeline transaction boundary

`EventProcessor._run_pipeline_in_transaction` defers repository `commit()` calls to a single flush + final commit:

- **Success** — Decision, Actions, and Report rows commit atomically.
- **Failure** — full rollback; event marked `failed` in a **separate** transaction so the failure is never lost.

External calls (Gemini, S3, Resend) run inside the action phase; a mid-pipeline exception rolls back DB state even if an S3 object was already uploaded (orphan objects possible — compensating delete not implemented).

### Action execution order

Recommendations are normalized and sorted before execution:

| Order | `action_type` | Integration |
|---|---|---|
| 0 | `report` | ReportLab → S3 → `reports` row |
| 1 | `email` | Resend (uses presigned S3 URL when available) |
| 2 | `notification` | Simulated result dict |
| 3 | `manual_review` | Fallback when recommendation is unrecognized |

Email failure does **not** abort subsequent actions; each action records its own `status` (`completed` | `failed`).

### Security model

| Control | Implementation |
|---|---|
| JWT auth | `python-jose` HS256; `get_current_user` dependency |
| Admin-only registration | `require_admin` on `POST /auth/register` |
| Startup validation | `SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`, `DATABASE_URL` required at boot |
| Inactive users | Login and token use return 403 |
| Production runtime | Gunicorn + 4 Uvicorn workers; non-root `appuser` in Docker |

### Health probes

| Endpoint | HTTP | Checks |
|---|---|---|
| `/health/live` | 200 always (if process up) | FastAPI process alive |
| `/health/ready` | 200 or 503 | `SELECT 1` on PostgreSQL + Redis `PING` |

Use `/health/ready` as the Render health check path.

### Gemini contract

`GeminiClient` expects JSON with:

```json
{
  "classification": "string",
  "summary": "string",
  "recommendations": ["send_email", "generate_report", "notify_team"]
}
```

Priority comes from the Rule Engine, not from Gemini. Payment-failure prompts instruct Gemini to include `send_email` and `generate_report` first.

---

## Tech stack

| Technology | Version (project) | Usage |
|---|---|---|
| **Python** | 3.12 (Docker / CI) | Runtime |
| **FastAPI** | ≥ 0.115 | REST API |
| **Uvicorn** | ≥ 0.32 | ASGI server (local dev) |
| **Gunicorn** | ≥ 23 | Production process manager (Render) |
| **PostgreSQL** | 16 (Docker) | Primary datastore |
| **SQLAlchemy** | ≥ 2.0 | ORM |
| **Alembic** | ≥ 1.14 | Migrations |
| **Redis** | 7 (Docker) | Celery broker and result backend |
| **Celery** | ≥ 5.4 | Background task queue |
| **Gemini** | `google-generativeai` ≥ 0.8 | Event analysis |
| **Stripe** | ≥ 11 | Webhook signature verification |
| **Resend** | ≥ 2.5 | Transactional email |
| **Amazon S3** | `boto3` ≥ 1.35 | PDF storage |
| **ReportLab** | ≥ 4.2 | PDF generation |
| **pytest** | ≥ 8.3 | Test suite (20 tests) |
| **ruff** | CI-only | Lint (`E`, `F`, `W`, `I`) |

---

## Getting started

### Prerequisites

| Tool | Purpose |
|---|---|
| **Docker** + **Docker Compose** | Run API, worker, Postgres, Redis |
| **Python 3.12+** | Optional: run tests or scripts on the host |
| **Git** | Clone the repository |

External accounts (required for full E2E behavior, not for unit tests):

- Stripe (webhook signing secret)
- Google AI / Gemini API key
- AWS S3 bucket and credentials
- Resend API key

### Local setup

**1. Clone and configure environment**

```bash
git clone https://github.com/Donovan-Nudrak/Business_Automation_Agent.git
cd Business_Automation_Agent
cp .env.example .env
```

Edit `.env` — minimum for startup:

| Variable | Required for startup |
|---|---|
| `SECRET_KEY` | **Yes** — must not be the default placeholder |
| `STRIPE_WEBHOOK_SECRET` | **Yes** — non-empty |
| `DATABASE_URL` | **Yes** — non-empty (Compose overrides host to `postgres`) |
| `GEMINI_API_KEY` | Required for AI analysis in the worker |
| `AWS_*` | Required for PDF upload |
| `RESEND_*`, `ALERT_EMAIL` | Required for email actions |

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

**2. Start services**

```bash
docker compose up --build
```

| Service | Port | Notes |
|---|---|---|
| `api` | `8000` | FastAPI with hot reload (`uvicorn --reload`) |
| `worker` | — | Celery worker |
| `postgres` | `5432` | Database `business_automation` |
| `redis` | `6379` | Broker / backend |

**3. Run migrations**

```bash
docker compose exec api alembic upgrade head
```

**4. Bootstrap first admin**

`POST /auth/register` requires admin JWT. Create the first admin:

```bash
docker compose exec api python -c "
from app.core.security import hash_password
from app.database.session import SessionLocal
from app.models.user import User

db = SessionLocal()
db.add(User(
    email='admin@example.com',
    hashed_password=hash_password('ChangeMe123!'),
    role='admin',
    active=True,
))
db.commit()
print('Admin created: admin@example.com')
"
```

**5. Verify**

| Check | URL / command |
|---|---|
| OpenAPI | http://localhost:8000/docs |
| Liveness | http://localhost:8000/health/live |
| Readiness | http://localhost:8000/health/ready |
| E2E smoke | `python scripts/smoke_test_e2e.py` |

### Environment variables

| Name | Description | Required |
|---|---|---|
| `APP_NAME` | Application title | No |
| `APP_ENV` | Environment label | No |
| `DEBUG` | FastAPI debug mode | No |
| `API_HOST` / `API_PORT` | Bind settings (local) | No |
| `DATABASE_URL` | PostgreSQL connection URL | **Yes** |
| `REDIS_URL` | Redis URL | Yes (worker + readiness) |
| `CELERY_BROKER_URL` | Celery broker | Yes (worker) |
| `CELERY_RESULT_BACKEND` | Celery result backend | Yes (worker) |
| `SECRET_KEY` | JWT signing secret | **Yes** (non-default) |
| `JWT_ALGORITHM` | JWT algorithm | No |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Token TTL | No |
| `GEMINI_API_KEY` | Google Gemini API key | Yes (analysis) |
| `GEMINI_MODEL` | Model name (e.g. `gemini-2.5-flash`) | No |
| `STRIPE_SECRET_KEY` | Stripe API secret | No (webhook-only flow) |
| `STRIPE_WEBHOOK_SECRET` | Stripe webhook signing secret | **Yes** |
| `AWS_ACCESS_KEY_ID` | AWS access key | Yes (reports) |
| `AWS_SECRET_ACCESS_KEY` | AWS secret key | Yes (reports) |
| `AWS_REGION` | S3 region | Yes (reports) |
| `AWS_S3_BUCKET` | S3 bucket name | Yes (reports) |
| `PRESIGNED_URL_EXPIRE_SECONDS` | Presigned URL TTL (default 86400) | No |
| `RESEND_API_KEY` | Resend API key | Yes (email) |
| `RESEND_FROM_EMAIL` | Sender address | Yes (email) |
| `ALERT_EMAIL` | Default alert recipient | Yes (email) |
| `TEST_DATABASE_URL` | Pytest database URL | Tests only |

Startup validation in `app/core/config.py` fails fast on invalid secrets.

### Running tests

```bash
TEST_DATABASE_URL=postgresql://postgres:postgres@localhost:5432/business_automation_test pytest tests/ -v
```

Celery is mocked in tests; Redis is not required.

---

## API reference

**13 endpoints** registered in `app/main.py`. Customer routes exist as placeholders but are not mounted.

| Method | Route | Auth | Description |
|---|---|---|---|
| `GET` | `/health/live` | None | Liveness probe |
| `GET` | `/health/ready` | None | Readiness probe (PostgreSQL + Redis) |
| `POST` | `/auth/register` | Admin JWT | Create user (`operator` role) |
| `POST` | `/auth/login` | None | Authenticate; returns JWT |
| `POST` | `/events` | JWT | Create manual event (`received`) |
| `GET` | `/events` | JWT | List events (pagination, filters) |
| `GET` | `/events/{event_id}` | JWT | Get event by ID |
| `POST` | `/webhooks/stripe` | Stripe signature | Ingest Stripe event; enqueue worker |
| `GET` | `/reports` | JWT | List reports |
| `GET` | `/reports/event/{event_id}` | JWT | Report for an event |
| `GET` | `/reports/{report_id}` | JWT | Report by ID |
| `GET` | `/actions` | JWT | List actions |
| `GET` | `/actions/{action_id}` | JWT | Action by ID |

| Auth label | Meaning |
|---|---|
| **None** | Public |
| **JWT** | `Authorization: Bearer <token>` |
| **Admin JWT** | JWT with `role=admin` |
| **Stripe signature** | Valid `Stripe-Signature` header |

---

## Operations

### CI

Workflow: `.github/workflows/ci.yml`

| Trigger | Branches |
|---|---|
| `push` / `pull_request` | `main`, `develop` |

Steps: PostgreSQL 16 service → Python 3.12 → `pip install -r requirements.txt` → `ruff check app/` → `pytest tests/ -v`.

### Deployment on Render

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/docs/deploy-fastapi)

Target architecture on Render:

```text
┌──────────────────┐     ┌──────────────────┐
│  Web Service     │     │  Worker Service  │
│  (Dockerfile)    │     │  (same image)    │
│  Gunicorn :8000  │     │  Celery worker   │
└────────┬─────────┘     └────────┬─────────┘
         │                          │
         └──────────┬───────────────┘
                    ▼
         ┌──────────────────────┐
         │  Render PostgreSQL   │
         │  Render Redis        │
         └──────────────────────┘
```

#### Web Service (API)

| Setting | Value |
|---|---|
| Runtime | Docker |
| Dockerfile | Root `Dockerfile` |
| Port | `8000` |
| Health check | `/health/ready` |
| Start command | Default from Dockerfile |

```bash
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000 --timeout 120
```

Release command (migrations):

```bash
alembic upgrade head
```

#### Worker Service (Celery)

| Setting | Value |
|---|---|
| Runtime | Docker (same image) |
| Start command | `celery -A app.tasks.celery_app worker --loglevel=info` |

Mirror all Web Service env vars (`DATABASE_URL`, `REDIS_URL`, `CELERY_*`, `GEMINI_*`, `AWS_*`, `RESEND_*`, `SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`).

#### Managed services

| Render service | Env vars |
|---|---|
| PostgreSQL | `DATABASE_URL` |
| Redis | `REDIS_URL`, `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND` |

Set secrets only in the Render dashboard — never commit `.env`.

### Project layout

```text
app/
├── api/routes/       # HTTP endpoints
├── agents/           # BusinessAgent
├── rules/            # RuleEngine
├── decision_engine/  # Gemini client
├── services/         # Domain services
├── action_executor/  # Action execution
├── repositories/     # Data access
├── models/           # SQLAlchemy models
├── tasks/            # Celery tasks
└── integrations/     # S3, Resend clients
tests/                # Pytest suite (20 tests)
scripts/              # smoke_test_e2e.py
alembic/              # Migrations
.github/workflows/    # CI
Dockerfile            # Production image (Render)
docker-compose.yml    # Local development only
```

---

## License

MIT License — see [LICENSE](LICENSE) for details.

