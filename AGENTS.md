# Lazy Rabbit Agent — Agent Guide

## Purpose

Multi-tenant LLM platform with AI agent factory, personal secretary agent, learning coach, and RAG-powered knowledge base. Enables rapid agent prototyping through declarative compilation from natural language specifications.

## Quick Start

```bash
# Setup (first time)
make install          # Install dependencies (backend + frontend)
make db-upgrade       # Apply database migrations
make db-seed          # Seed RBAC roles/permissions

# Daily workflow
make check            # Run all critical checks (test + lint + type-check)
make start            # Start backend + frontend
make type-sync        # Keep frontend types in sync with backend (after backend changes)

# Before commit
make check            # Verify all tests pass
make type-sync        # Ensure types match backend schema
make format           # Auto-format code
```

## Repository Map

```
lazy-rabbit-agent/
├── backend/              # FastAPI REST API (Python 3.8+, Poetry, SQLAlchemy, LangGraph)
│   ├── app/
│   │   ├── api/v1/       # REST endpoints (auth, users, secretary, factory, memory, etc.)
│   │   ├── services/     # Business logic (agent_factory, secretary_agent, coach, RAG)
│   │   ├── models/       # SQLAlchemy ORM models
│   │   ├── schemas/      # Pydantic request/response schemas
│   │   └── core/         # Config, security, database
│   ├── tests/            # Pytest tests (20+ test files)
│   └── alembic/          # Database migrations
├── frontend/             # Vue 3 SPA (TypeScript, Vite, Pinia, Element Plus)
│   ├── src/
│   │   ├── views/        # Page components (AgentFactory, Secretary, Learning, etc.)
│   │   ├── components/   # Reusable Vue components
│   │   ├── stores/       # Pinia state management
│   │   ├── services/     # API clients
│   │   └── types/        # TypeScript definitions (api.generated.ts is auto-generated)
│   ├── tests/            # Vitest unit + Playwright E2E tests
│   └── scripts/          # Type generation scripts
├── docs/                 # Sphinx documentation + architecture guides
├── example/              # LangChain demos, agent examples, fixtures
└── Makefile              # Unified command interface (40+ targets)
```

## Key Technologies

**Backend**: FastAPI, Pydantic, SQLAlchemy, LangChain/LangGraph, Alembic, Poetry  
**Frontend**: Vue 3, TypeScript, Vite, Pinia, Axios, Playwright  
**AI/LLM**: OpenAI-compatible APIs (DeepSeek, GPT, Claude), LangGraph ReAct agents  
**Database**: SQLite (dev), PostgreSQL (prod), Alembic migrations  
**Type Safety**: openapi-typescript auto-generates frontend types from backend OpenAPI schema

## Commands

### Verification (Run Before Commit)
```bash
make check            # Run all checks (lint + type-check + test)
make test             # Run all tests (backend pytest + frontend vitest + E2E)
make lint             # Run linters (black + flake8 + eslint)
make type-check       # TypeScript type checking (vue-tsc)
make type-sync        # Regenerate + validate TypeScript types from backend
```

### Development
```bash
make start            # Start backend (port 8000) + frontend (port 5173)
make stop             # Stop all services
make restart          # Restart all services
make start-backend    # Backend only
make start-frontend   # Frontend only (port 5173)
```

### Database
```bash
make db-migrate       # Create new migration (prompts for message)
make db-upgrade       # Apply pending migrations
make db-status        # Show current migration status
make db-reset         # ⚠️ DESTRUCTIVE: Delete DB and reseed (requires confirmation)
```

### Code Quality
```bash
make format           # Auto-format (black + prettier)
make lint             # Check linting
make test-coverage    # Run tests with coverage report
make test-e2e         # Run Playwright E2E tests
```

### Type Safety (Critical for Type Correctness)
```bash
make generate-types   # Generate TypeScript types from OpenAPI schema
make type-check       # Validate TypeScript types
make type-sync        # Generate + validate (run after backend schema changes)
```

See `docs/TYPE_SAFETY_HARNESS.md` for details on the type generation system.

## Architecture Boundaries

### Layering (Backend)
```
API Layer (app/api/v1/endpoints/)
    ↓ calls
Service Layer (app/services/)
    ↓ calls
Data Layer (app/models/)
    ↓ accesses
Database (SQLAlchemy/SQLite/PostgreSQL)
```

**Rules**:
- API endpoints call services, never directly access models
- Services contain business logic, orchestrate models and external APIs
- Models are thin ORM wrappers (no business logic)
- Database access only through SQLAlchemy ORM (no raw SQL)

### Layering (Frontend)
```
Views (src/views/)
    ↓ uses
Components (src/components/)
    ↓ reads/writes
Stores (src/stores/ - Pinia)
    ↓ calls
Services (src/services/ - API clients)
    ↓ HTTP
Backend API
```

**Rules**:
- Views/Components never call API directly (use stores)
- Stores manage state and call services
- Services are thin API client wrappers (no business logic)
- Always use types from `src/types/api.generated.ts` (auto-generated)

### Danger Zones

**High-risk areas requiring extra caution**:
- `backend/app/core/security.py` — JWT token handling, password hashing
- `backend/app/services/agent_factory/compiler.py` — LLM-based code generation
- `backend/app/services/secretary_agent/tools/` — Tool implementations with external effects
- `backend/alembic/versions/` — Database migrations (irreversible)
- `frontend/src/services/api.ts` — Auth token interceptors
- `.env` — Secrets and API keys (never commit)

## Safety Boundaries

### DO NOT (Without Explicit User Approval)

1. **Secrets & Credentials**
   - ❌ Never commit `.env`, `.env.local`, or any file containing secrets
   - ❌ Never log API keys, tokens, passwords, or PII
   - ❌ Never hardcode secrets in code
   - ✅ Always use environment variables via `app/core/config.py`
   - ✅ Use `.env.sample` as template (committed), `.env` for real secrets (git-ignored)

2. **Destructive Git Operations**
   - ❌ `git reset --hard` (loses uncommitted work)
   - ❌ `git push --force` to main/master
   - ❌ `git clean -f` (deletes untracked files)
   - ✅ Ask user before any destructive operation
   - ✅ Prefer `git stash` over resetting

3. **Database Operations**
   - ❌ `make db-reset` (deletes all data)
   - ❌ Manual SQL against production database
   - ❌ Modifying migration files after they're merged
   - ✅ Always create new migrations (`make db-migrate`)
   - ✅ Test migrations locally before applying to production

4. **Deployment & Production**
   - ❌ Direct database access in production
   - ❌ Deploying without running `make check` first
   - ❌ Skipping CI checks (when CI is added)
   - ✅ Deploy only from approved branches
   - ✅ Follow blue-green deployment pattern

5. **Test Integrity**
   - ❌ Modifying test fixtures to make failing tests pass
   - ❌ Commenting out failing tests without fixing root cause
   - ❌ Skipping E2E tests for "speed"
   - ✅ Investigate test failures, don't paper over them
   - ✅ Add tests for new features/bug fixes

6. **Type Safety**
   - ❌ Bypassing TypeScript errors with `@ts-ignore` or `any`
   - ❌ Manually editing `src/types/api.generated.ts` (it's auto-generated)
   - ❌ Committing code without running `make type-check`
   - ✅ Run `make type-sync` after backend schema changes
   - ✅ Fix type errors properly, don't suppress them

## Definition of Done

Before marking work complete or requesting review:

### Code Quality
- [ ] All tests pass: `make test` (pytest + vitest + E2E)
- [ ] Linting passes: `make lint` (no warnings)
- [ ] Code is formatted: `make format` (black + prettier)
- [ ] Types are correct: `make type-check` (no TypeScript errors)
- [ ] Types are in sync: `make type-sync` (after backend changes)

### Functionality
- [ ] Feature works end-to-end (manual testing)
- [ ] E2E critical paths verified: `make test-e2e`
- [ ] Error cases handled gracefully
- [ ] Loading/empty states implemented

### Documentation
- [ ] API changes documented in OpenAPI schema (auto-generated docs)
- [ ] Complex logic has explanatory comments (sparingly)
- [ ] README updated if setup changed
- [ ] This AGENTS.md updated if boundaries changed

### Safety
- [ ] No secrets committed (check `.env`, logs, comments)
- [ ] No destructive operations without user confirmation
- [ ] Test fixtures not modified to force tests to pass
- [ ] Database migrations tested locally

### Final Check
```bash
# Run this before every commit
make check && make type-sync && git status
```

## AI Agent Factory

The **Agent Factory** (孵化器) is a parent agent that compiles natural language specifications into runnable child agents.

**Pipeline**: `一句话 → AgentSpec (8 slots) → 人工审核 → 装配运行`

**Key Files**:
- `backend/app/services/agent_factory/compiler.py` — LLM-based spec compilation
- `backend/app/services/agent_factory/assembler.py` — ReAct agent assembly
- `backend/app/services/agent_factory/spec.py` — 8-slot blueprint (role, brain, memory, tools, policies, prompts, acceptance, workflow)
- `backend/app/api/v1/endpoints/factory.py` — Factory REST API
- `frontend/src/views/AgentFactory.vue` — Factory UI
- `docs/agent_specs/` — Spec templates and examples

**8 Slots**: one_liner → role → brain → memory → tools → policies → prompts → acceptance (→ workflow)

**Safety**: Tool registry (read-only), human approval required before running, isolated memory per agent

## Memory System

**Short-term memory**: Conversation context (LangChain default)  
**Long-term memory**: File-based JSONL storage per agent (`data/agent_memory/agent_{id}/memories.jsonl`)

**Key Files**:
- `backend/app/services/memory/file_memory.py` — File-based memory backend
- `backend/app/api/v1/endpoints/memory.py` — Memory REST API
- Search: Uses ripgrep (rg) for fast text search, falls back to grep/Python

**Auto-saving**: Agent conversations are automatically saved to long-term memory if enabled in AgentSpec

## Common Tasks

### Adding a New API Endpoint

1. Define Pydantic schemas in `backend/app/schemas/`
2. Create endpoint in `backend/app/api/v1/endpoints/`
3. Register router in `backend/app/api/v1/api.py`
4. Restart backend: `make restart-backend`
5. Regenerate frontend types: `make generate-types`
6. Import types in frontend: `import type { components } from '@/types/api.generated'`
7. Create service in `frontend/src/services/`
8. Add tests: `backend/tests/test_*.py` and `frontend/tests/unit/`

### Adding a New Agent Tool

1. Create tool in `backend/app/services/secretary_agent/tools/`
2. Register in tool registry: `backend/app/services/agent_factory/registry.py`
3. Add to AgentSpec tool options
4. Write tests: `backend/tests/test_utility_tools.py`
5. Document in `docs/agent_specs/AGENT_SPEC_TEMPLATE.md`

### Fixing Type Mismatches

```bash
# After backend Pydantic model changes
make restart-backend    # Reload OpenAPI schema
make generate-types     # Regenerate TypeScript types
make type-check         # Find type errors
# Fix TypeScript errors in IDE
git add frontend/src/types/api.generated.ts
```

See `docs/TYPE_SAFETY_HARNESS.md` for comprehensive guide.

## Troubleshooting

### "Backend not running" during type generation
```bash
make start-backend
sleep 3
make generate-types
```

### "Types out of sync" errors
```bash
make type-sync  # Regenerates + validates types
```

### Database migration conflicts
```bash
make db-status           # Check current state
make db-downgrade        # Rollback last migration
# Fix conflict manually
make db-migrate          # Create new migration
```

### Tests failing after changes
```bash
make test-backend        # Run backend tests only
make test-frontend       # Run frontend tests only
make test-e2e            # Run E2E tests only
```

### Port already in use
```bash
make stop                # Stop all services
lsof -ti:8000 | xargs kill  # Force kill backend
lsof -ti:5173 | xargs kill  # Force kill frontend
make start
```

## Getting Help

- **Documentation**: `docs/source/` (Sphinx docs), `README.md`
- **Architecture**: `docs/source/02-architecture.md`
- **Type Safety**: `docs/TYPE_SAFETY_HARNESS.md`, `frontend/TYPE_GENERATION.md`
- **Agent Factory**: `docs/agent_specs/AGENT_SPEC_TEMPLATE.md`
- **API Reference**: http://localhost:8000/docs (OpenAPI/Swagger UI)
- **Issues**: Report bugs/features at project repository

## Maintenance

**Owner**: Project maintainer (update this with actual owner)  
**Review Cadence**: This guide should be reviewed quarterly or after major architecture changes  
**Last Updated**: 2026-07-31

---

**Remember**: When in doubt, run `make check` before committing. Type safety is enforced — use `make type-sync` after backend changes.
