# Phase 1 Foundation — Master Sequencing Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Bootstrap the full-stack foundation (Data Layer → Backend API → Background Jobs → Frontend SPA) so every Phase 2 feature work order has stable infrastructure to build on.

**Architecture:** Four WOs are built in dependency order with a shared prerequisites step first. The Data Layer is first (Aurora/SQLModel/S3/Redis + Job model). The Backend Foundation follows (FastAPI, Cognito, CORS, audit log, HTTP wrappers). Background Job Infrastructure comes next (Celery, LangGraph, LLM router, ECS). The Frontend SPA is last — its route/context scaffolding is parallel-safe, but `useApi` and `useJobPoller` depend on confirmed backend API contracts from WO-1/WO-2.

**Tech Stack:** Python/FastAPI, SQLModel==0.0.24, SQLAlchemy>=2.0.14<2.1, Alembic==1.15.2, Aurora PostgreSQL, asyncpg, Celery==5.5.3, Kombu==5.5.*, Redis>=4.5.2<5.3, LangGraph + langgraph-checkpoint-postgres (pinned to same minor), AWS Cognito, AWS S3/Boto3, AWS ECS/Fargate, Vite, React 18, TypeScript strict, shadcn/ui, Tailwind, AWS Amplify v6, react-router-dom@6.30.1.

---

## Scope Note

Each of the four work orders is a self-contained subsystem. This master plan establishes the **execution order, pinned versions, and inter-WO interface contracts**. When you begin each WO, invoke `superpowers:writing-plans` again to produce a detailed TDD plan for that WO. Do not implement all four WOs from this document alone.

---

## Dependency Graph

```
[WO-0: Shared Prerequisites] ─────────────────────────────────────────┐
 (Settings module, Job model, docker-compose, env schema)             │
        │                                                             │
        ▼                                                             │
WO-3: Data Layer ──────────────────────────────────────────────────►WO-2: Background Job Infrastructure
      (SQLModel session, S3 client, Redis broker/backend URLs,        (Celery, LangGraph + checkpointer,
       Job/TaskRun DB model, BaseRepository[workspace-scoped])         LLM router, ECS task defs)
            │
            ▼
WO-1: Backend Foundation
      (FastAPI app, Cognito JWT, CORS, workspace enforcement,
       error schema + correlation ID, audit log, HTTP wrappers)
            │
            │ (API contracts confirmed: job status shape, error envelope)
            ▼
WO-4: Frontend Foundation
      (Vite/React SPA, Amplify v6, AuthContext, WorkspaceContext,
       useApi with typed ErrorResponse, useJobPoller, routing)
```

**Partial parallelism:** WO-4 route tree, page placeholders, AuthContext, and WorkspaceContext can be scaffolded in parallel with WO-1/WO-2. `useApi` and `useJobPoller` must wait for confirmed backend contracts.

---

## Execution Order

| Step | Work Order | Hard Depends On | Partial Parallel OK |
|------|-----------|-----------------|---------------------|
| 0 | **Shared Prerequisites** | Nothing | — |
| 1 | **WO-3: Data Layer Foundation** | WO-0 | WO-4 shell (routes/contexts) |
| 2 | **WO-1: Backend Foundation** | WO-3 | WO-4 shell |
| 3 | **WO-2: Background Job Infrastructure** | WO-3 + WO-1 | WO-4 shell |
| 4 | **WO-4: Frontend Foundation (complete)** | WO-1 + WO-2 contracts | — |

---

## WO-0: Shared Prerequisites

These must exist before any work order begins. One engineer does this once.

### Pinned Package Versions

```toml
# pyproject.toml (backend)
[tool.poetry.dependencies]
python = "^3.12"
fastapi = ">=0.115,<0.116"
sqlmodel = "0.0.24"
sqlalchemy = ">=2.0.14,<2.1"
alembic = "1.15.2"
asyncpg = ">=0.29"
pydantic-settings = ">=2.0"
celery = "5.5.3"
kombu = ">=5.5,<5.6"
redis = ">=4.5.2,<5.3"
langgraph = ">=0.2,<0.3"
langgraph-checkpoint = ">=0.2,<0.3"
langgraph-checkpoint-postgres = ">=0.2,<0.3"
httpx = ">=0.27"          # for integration HTTP clients
tenacity = ">=8.2"        # retry logic
boto3 = ">=1.34"
python-jose = {extras = ["cryptography"], version = ">=3.3"}
```

```json
// package.json (frontend)
{
  "dependencies": {
    "react": "^18.3.1",
    "react-dom": "^18.3.1",
    "react-router-dom": "6.30.1",
    "aws-amplify": "^6.0.0",
    "@aws-amplify/ui-react": "^6.0.0"
  },
  "devDependencies": {
    "vite": "^5.4",
    "typescript": "^5.5",
    "vitest": "^2.0",
    "@testing-library/react": "^16.0",
    "tailwindcss": "^3.4"
  }
}
```

### Shared Settings Module

Create `backend/app/config.py` first — all WOs import from here.

```python
# backend/app/config.py
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Database
    database_url: str                    # asyncpg URL: postgresql+asyncpg://...
    # Redis — separate broker and result backend (Celery requires explicit split)
    celery_broker_url: str               # redis://host:6379/0
    celery_result_backend: str           # redis://host:6379/1
    # AWS
    aws_region: str = "us-east-1"
    aws_s3_bucket: str
    # Cognito
    cognito_user_pool_id: str
    cognito_client_id: str
    cognito_region: str = "us-east-1"
    # LLM providers
    anthropic_api_key: str
    openai_api_key: str
    # Integrations
    crustdata_api_key: str
    browser_use_api_key: str
    unipile_api_key: str
    unipile_base_url: str

settings = Settings()
```

### Job / TaskRun DB Model

Define before WO-3 or WO-2 to prevent schema ambiguity at lifecycle write time.

```python
# backend/app/models/job.py
import enum
from datetime import datetime
from uuid import UUID, uuid4
from sqlmodel import SQLModel, Field

class JobStatus(str, enum.Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"

class Job(SQLModel, table=True):
    __tablename__ = "jobs"
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    workspace_id: UUID = Field(index=True, foreign_key="workspaces.id")
    task_type: str                         # e.g. "gtm_thesis", "enrichment"
    celery_task_id: str | None = None
    status: JobStatus = JobStatus.PENDING
    error: str | None = None
    result: dict | None = Field(default=None, sa_column_kwargs={"type_": "JSON"})
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
```

### Docker Compose (local dev)

```yaml
# docker-compose.yml
version: "3.9"
services:
  postgres:
    image: postgres:16
    environment:
      POSTGRES_USER: predict
      POSTGRES_PASSWORD: predict
      POSTGRES_DB: predict
    ports: ["5432:5432"]
  redis:
    image: redis:7-alpine
    ports: ["6379:6379"]
  backend:
    build: ./backend
    env_file: ./backend/.env
    ports: ["8000:8000"]
    depends_on: [postgres, redis]
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
  worker:
    build: ./backend
    env_file: ./backend/.env
    depends_on: [postgres, redis]
    command: celery -A app.celery_app worker --loglevel=info --queues=default -c 4
  frontend:
    build: ./frontend
    env_file: ./frontend/.env
    ports: ["5173:5173"]
    command: npm run dev -- --host
```

### Prerequisites Checklist

- [ ] `pyproject.toml` with pinned versions above
- [ ] `backend/app/config.py` (Settings, `settings` singleton)
- [ ] `backend/app/models/__init__.py` + `backend/app/models/job.py` (Job model + JobStatus enum)
- [ ] `backend/.env.example` with all keys from Settings documented
- [ ] `docker-compose.yml` for local postgres + redis + backend + worker + frontend
- [ ] `frontend/package.json` with pinned versions above
- [ ] `frontend/.env.example` with all `VITE_*` vars documented
- [ ] GitHub repo with `main` branch protection; CI: `pytest` (backend) + `vitest` (frontend) on every PR

---

## WO-3: Data Layer Foundation Setup

**Blueprint:** Data Layer (`daf35d14-79da-498e-be4b-36e5942626d0`)

### File Structure

```
backend/
  app/
    db/
      __init__.py
      base.py          # SQLModel metadata, async engine factory
      session.py       # get_db async generator dependency
    s3/
      __init__.py
      client.py        # Boto3 wrapper: presigned PUT/GET, short expiry
    repositories/
      __init__.py
      base.py          # BaseRepository[T] with workspace-scoped list()
      job.py           # JobRepository with update_status()
  alembic/
    env.py             # Async Alembic env (async_engine_from_config + run_sync)
    versions/
      0001_initial.py  # Baseline migration (jobs table)
  alembic.ini
  tests/
    db/
      test_session.py
    s3/
      test_client.py
    repositories/
      test_base.py
      test_job.py
```

### Key Interface Contracts

```python
# backend/app/db/session.py
async def get_db() -> AsyncGenerator[AsyncSession, None]: ...

# backend/app/s3/client.py
def get_presigned_put_url(key: str, expires_in: int = 300) -> str: ...
def get_presigned_get_url(key: str, expires_in: int = 300) -> str: ...

# backend/app/repositories/base.py
class BaseRepository(Generic[T]):
    def __init__(self, db: AsyncSession) -> None: ...
    async def get(self, id: UUID) -> T | None: ...
    async def list(self, workspace_id: UUID, **filters) -> list[T]: ...  # always workspace-scoped
    async def create(self, obj: T) -> T: ...
    async def update(self, obj: T) -> T: ...
    async def delete(self, id: UUID) -> None: ...

# backend/app/repositories/job.py
class JobRepository(BaseRepository[Job]):
    async def update_status(
        self,
        job_id: UUID,
        status: JobStatus,
        error: str | None = None,
        result: dict | None = None,
    ) -> Job: ...
```

### Alembic Async env.py Gotcha

The async env.py must use `run_sync` to run migrations; import all SQLModel table classes before calling `target_metadata` or autogenerate produces empty migrations:

```python
# alembic/env.py (critical pattern)
from sqlalchemy.ext.asyncio import async_engine_from_config
from sqlmodel import SQLModel
import app.models.job  # noqa: F401 — import all table models here

target_metadata = SQLModel.metadata

def run_migrations_online() -> None:
    connectable = async_engine_from_config(config.get_section(config.config_ini_section))
    async def do_run(connection):
        context.configure(connection=connection, target_metadata=target_metadata,
                          compare_type=True, naming_convention={
                              "ix": "ix_%(column_0_label)s",
                              "uq": "uq_%(table_name)s_%(column_0_name)s",
                              "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
                              "pk": "pk_%(table_name)s",
                          })
        async with context.begin_transaction():
            await connection.run_sync(context.run_migrations)
    asyncio.run(connectable.connect().run_sync(lambda conn: asyncio.run(do_run(conn))))
```

### Major Tasks

- [ ] Async engine factory + `get_db` session dependency (`db/base.py`, `db/session.py`)
- [ ] Alembic `env.py` with async engine + full metadata import (see gotcha above)
- [ ] Initial migration generating `jobs` table; run and verify applies cleanly
- [ ] S3 Boto3 wrapper reading bucket from `settings.aws_s3_bucket` (`s3/client.py`)
- [ ] `BaseRepository[T]` with workspace-scoped `list()` (`repositories/base.py`)
- [ ] `JobRepository` with `update_status()` (`repositories/job.py`)
- [ ] Tests (pytest-asyncio) for session factory, S3 wrapper (mocked boto3), base + job repositories

---

## WO-1: Backend Foundation Setup

**Blueprint:** Backend (`f6cc0a50-d1c0-40f1-b340-e07b2136d2e9`)

### File Structure

```
backend/
  app/
    main.py              # FastAPI app factory, CORS, middleware, routers, exception handlers
    dependencies.py      # get_current_user, get_db re-export
    errors.py            # ErrorResponse schema, exception handlers
    audit.py             # Immutable audit log writer
    middleware/
      cognito.py         # JWKS fetch + JWT validation
    api/v1/
      router.py          # Mounts domain routers
      common/router.py   # GET /api/v1/health
      workspace/router.py
      events/router.py
      enrichment/router.py
      outreach/router.py
      agents/router.py   # GET /api/v1/agents/jobs/{job_id} — job status endpoint
    integrations/
      base.py            # BaseIntegrationClient (httpx, tenacity retry, rate limit)
      crustdata.py
      browser_use.py
      unipile.py
  tests/
    test_health.py
    test_auth.py
    test_errors.py
    test_audit.py
    test_job_status.py
    integrations/
      test_crustdata.py
      test_browser_use.py
      test_unipile.py
```

### Key Interface Contracts

```python
# backend/app/dependencies.py
class UserContext(BaseModel):
    user_id: UUID
    workspace_id: UUID
    email: str
    role: Literal["customer", "gtm_engineer"]

async def get_current_user(token: str = Depends(oauth2_scheme)) -> UserContext: ...

# backend/app/errors.py
class ErrorResponse(BaseModel):
    error_code: str
    message: str
    correlation_id: str      # UUID generated per request for debugging
    detail: dict | None = None

# backend/app/audit.py
async def write_audit_log(
    db: AsyncSession,
    event_type: Literal["state_transition", "send_action", "approval_change", "evidence_mutation"],
    actor_id: UUID,
    resource_id: UUID,
    resource_type: str,
    before: dict | None,
    after: dict | None,
) -> None: ...

# backend/app/api/v1/agents/router.py — job status API (consumed by useJobPoller)
# GET /api/v1/agents/jobs/{job_id}
# Response:
class JobStatusResponse(BaseModel):
    job_id: UUID
    status: JobStatus          # pending | in_progress | completed | failed
    task_type: str
    result: dict | None
    error: str | None
    created_at: datetime
    updated_at: datetime
```

### CORS Configuration (required for Amplify auth)

```python
# backend/app/main.py
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,   # add to Settings: list[str]
    allow_credentials=True,                   # required for Cognito JWT cookies
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### Major Tasks

- [ ] CORS middleware with `allow_credentials=True` (`main.py`)
- [ ] `config.py` extended with `allowed_origins: list[str]`
- [ ] Cognito JWKS fetcher + JWT validator (cache JWKS, validate signature + expiry + aud claim) (`middleware/cognito.py`)
- [ ] `get_current_user` dependency extracting `UserContext` (user_id, workspace_id, role) from token claims
- [ ] `ErrorResponse` with `correlation_id` + global exception handlers (`errors.py`)
- [ ] Request ID middleware attaching `X-Correlation-ID` header
- [ ] `GET /api/v1/health` returning `{"status": "ok"}`
- [ ] `GET /api/v1/agents/jobs/{job_id}` returning `JobStatusResponse` (uses `JobRepository`)
- [ ] Immutable audit log table (no PK update/delete) + `write_audit_log()` (`audit.py`)
- [ ] `BaseIntegrationClient` with httpx async client, tenacity retry (3 attempts, exponential backoff), auth header injection (`integrations/base.py`)
- [ ] Crustdata, Browser Use, Unipile clients extending `BaseIntegrationClient`
- [ ] Tests: JWT validation (valid/expired/wrong-aud), health, job status, error schema, audit log, HTTP wrappers (respx mocks)

---

## WO-2: Background Job Infrastructure

**Blueprint:** Backend (`f6cc0a50-d1c0-40f1-b340-e07b2136d2e9`)

### File Structure

```
backend/
  app/
    celery_app.py          # Celery factory using settings.celery_broker_url / celery_result_backend
    tasks/
      base.py              # IdempotentTask: retry + JobRepository.update_status()
    workflows/
      base_graph.py        # LangGraph base graph + AsyncPostgresSaver checkpointer
      state.py             # Base Pydantic state shared across node boundaries
    llm/
      router.py            # route_llm_call(task_type, prompt, response_model?) -> str | BaseModel
      claude_client.py
      openai_client.py
  ecs/
    api_task_def.json
    worker_task_def.json
  tests/
    tasks/test_base_task.py
    workflows/test_base_graph.py
    llm/test_router.py
```

### Key Interface Contracts

```python
# backend/app/celery_app.py
celery_app = Celery(
    "predict",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)

# backend/app/tasks/base.py
class IdempotentTask(celery.Task):
    abstract = True
    max_retries = 3
    # on_failure writes JobStatus.FAILED via JobRepository.update_status()
    # on_success writes JobStatus.COMPLETED

# backend/app/workflows/base_graph.py
async def build_base_graph(
    state_schema: type[BaseModel],
    thread_id: str,               # propagated from Job.id str; required by checkpointer
) -> CompiledStateGraph:
    """
    Pre-configures:
    - AsyncPostgresSaver checkpointer (requires .setup() call on first run per thread)
    - HITL pause node pattern (interrupt_before=["human_review"])
    - Conditional edges: approved → continue, rejected → retry, iteration >= 2 → escalate_gtme
    """

# backend/app/llm/router.py
class TaskType(str, Enum):
    GTM_THESIS = "gtm_thesis"
    STRUCTURED_EXTRACTION = "structured_extraction"
    ENTITY_RESOLUTION = "entity_resolution"
    MESSAGE_GENERATION = "message_generation"

async def route_llm_call(
    task_type: TaskType,
    prompt: str,
    response_model: type[BaseModel] | None = None,  # None → returns str; set → returns parsed model
    **kwargs,
) -> str | BaseModel: ...
```

### LangGraph Checkpointer Gotcha

`AsyncPostgresSaver` requires `.setup()` to create its internal tables before first use. Call it once at worker startup, not per-task:

```python
# In Celery worker startup signal
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

@celery_app.on_after_finalize.connect
def setup_langgraph(sender, **kwargs):
    import asyncio
    async def _setup():
        async with AsyncPostgresSaver.from_conn_string(settings.database_url) as saver:
            await saver.setup()
    asyncio.run(_setup())
```

### Major Tasks

- [ ] Celery factory using `settings.celery_broker_url` + `settings.celery_result_backend` (`celery_app.py`)
- [ ] Celery worker entrypoint in docker-compose: `celery -A app.celery_app worker --loglevel=info --queues=default -c 4`
- [ ] `IdempotentTask` base class: exponential backoff retry, `on_failure` → `JobStatus.FAILED`, `on_success` → `JobStatus.COMPLETED` (`tasks/base.py`)
- [ ] `AsyncPostgresSaver` setup in worker startup signal (see gotcha above)
- [ ] `build_base_graph()` with checkpointer, HITL pause node, two-iteration escalation edges (`workflows/base_graph.py`)
- [ ] Shared base state Pydantic model (`workflows/state.py`)
- [ ] `route_llm_call()` with `response_model` param for structured extraction paths (`llm/router.py`)
- [ ] Claude + OpenAI client wrappers (`llm/claude_client.py`, `llm/openai_client.py`)
- [ ] ECS Fargate task definitions for API + worker containers (`ecs/`)
- [ ] Tests: IdempotentTask retry/lifecycle, graph builds with checkpointer, LLM router dispatches correct client, `response_model` path returns parsed model

---

## WO-4: Frontend Foundation Setup

**Blueprint:** Frontend (`23413a97-3b66-4966-9556-353a5c75840f`)

### File Structure

```
frontend/
  index.html
  vite.config.ts       # path aliases: @/ → src/
  tsconfig.json        # strict: true, paths sync with vite aliases
  tailwind.config.ts
  src/
    main.tsx           # Amplify.configure() called HERE before React renders
    App.tsx            # React Router v6 route tree
    lib/
      amplify.ts       # Amplify.configure() config object (imported by main.tsx)
    contexts/
      AuthContext.tsx
      WorkspaceContext.tsx
    hooks/
      useApi.ts
      useJobPoller.ts
    components/
      ProtectedRoute.tsx
    pages/
      SignIn.tsx
      Onboarding.tsx
      WorkspaceHome.tsx
      ThesisPage.tsx
      EventDetail.tsx
      AccountDetail.tsx
  tests/
    contexts/AuthContext.test.tsx
    contexts/WorkspaceContext.test.tsx
    hooks/useApi.test.ts
    hooks/useJobPoller.test.ts
    components/ProtectedRoute.test.tsx
```

### Key Interface Contracts

```typescript
// src/hooks/useApi.ts — typed error envelope matches backend ErrorResponse
interface ApiError {
  error_code: string;
  message: string;
  correlation_id: string;
  detail?: Record<string, unknown>;
}

function useApi(): {
  get: <T>(path: string) => Promise<T>;
  post: <T>(path: string, body: unknown) => Promise<T>;
  put: <T>(path: string, body: unknown) => Promise<T>;
  del: (path: string) => Promise<void>;
  loading: boolean;
  error: ApiError | null;
}

// src/hooks/useJobPoller.ts — terminal states match JobStatus enum from backend
type JobStatus = "pending" | "in_progress" | "completed" | "failed";

function useJobPoller(
  jobId: string | null,
  options?: {
    intervalMs?: number;                            // default: 3000
    onComplete?: (result: Record<string, unknown>) => void;
    onFailed?: (error: string) => void;
  }
): { status: JobStatus | null }

// src/contexts/AuthContext.tsx
interface AuthContextValue {
  user: { username: string; email: string } | null;
  isAuthenticated: boolean;
  signOut: () => Promise<void>;
}

// src/contexts/WorkspaceContext.tsx
interface WorkspaceContextValue {
  workspaceId: string | null;
  setWorkspaceId: (id: string) => void;
}
```

### Amplify v6 Gotcha — configure() placement

Amplify v6 uses functional API. `Amplify.configure()` **must** run synchronously at module load before any React component mounts:

```typescript
// src/lib/amplify.ts
import { Amplify } from "aws-amplify";

Amplify.configure({
  Auth: {
    Cognito: {
      userPoolId: import.meta.env.VITE_COGNITO_USER_POOL_ID,
      userPoolClientId: import.meta.env.VITE_COGNITO_CLIENT_ID,
      loginWith: { email: true },
    },
  },
});
```

```typescript
// src/main.tsx — import amplify.ts FIRST, before React imports
import "@/lib/amplify";       // side-effect: configures Amplify
import React from "react";
import ReactDOM from "react-dom/client";
import App from "@/App";
// ...
```

### Vite Path Alias (TypeScript sync required)

```typescript
// vite.config.ts
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "path";

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: { "@": path.resolve(__dirname, "./src") },
  },
});
```

```json
// tsconfig.json — must match vite alias exactly
{
  "compilerOptions": {
    "strict": true,
    "baseUrl": ".",
    "paths": { "@/*": ["./src/*"] }
  }
}
```

### Major Tasks

- [ ] Vite scaffold with React 18, TypeScript strict, Tailwind, path alias `@/ → src/`
- [ ] shadcn/ui init (`npx shadcn-ui@latest init`)
- [ ] `src/lib/amplify.ts` with Amplify v6 `Amplify.configure()` call
- [ ] `src/main.tsx` importing amplify.ts as first side-effect import
- [ ] `AuthContext` using Amplify v6 `fetchAuthSession()` / `signIn()` / `signOut()` (`contexts/AuthContext.tsx`)
- [ ] `WorkspaceContext` with `workspaceId` + `setWorkspaceId` (`contexts/WorkspaceContext.tsx`)
- [ ] `useApi` hook with JWT from `fetchAuthSession().tokens.idToken`, typed `ApiError` envelope (`hooks/useApi.ts`)
- [ ] `useJobPoller` polling `GET /api/v1/agents/jobs/{jobId}` every `intervalMs` until terminal state (`hooks/useJobPoller.ts`)
- [ ] `ProtectedRoute` redirecting unauthenticated users to `/sign-in` (`components/ProtectedRoute.tsx`)
- [ ] React Router v6 nested route tree (all 6 routes, placeholder page components) (`App.tsx`)
- [ ] Vitest + React Testing Library tests for all hooks, contexts, and ProtectedRoute
- [ ] `frontend/.env.example` documenting `VITE_COGNITO_USER_POOL_ID`, `VITE_COGNITO_CLIENT_ID`, `VITE_API_BASE_URL`

---

## Phase 2 Readiness Checklist

- [ ] **WO-0:** docker-compose up with postgres + redis working, `.env` files in place
- [ ] **WO-3:** `pytest` green, Alembic baseline migration applied to local + staging DB, `get_db` importable, `JobRepository.update_status()` tested
- [ ] **WO-1:** `pytest` green, `GET /api/v1/health` → 200, `GET /api/v1/agents/jobs/{id}` → correct `JobStatusResponse`, Cognito JWT validation working against real User Pool, CORS headers present on preflight
- [ ] **WO-2:** `pytest` green, Celery worker connects to Redis and processes a no-op task, LangGraph base graph builds with real `AsyncPostgresSaver` checkpointer, LLM router dispatches to Claude for `GTM_THESIS` and OpenAI for `STRUCTURED_EXTRACTION`
- [ ] **WO-4:** `vitest` green, Amplify auth flow works against real Cognito User Pool, all 6 routes render without errors, `useApi` attaches `Authorization: Bearer` header on every call, `useJobPoller` polls and calls `onComplete` on `completed` status
