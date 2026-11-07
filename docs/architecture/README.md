# ShortlistAI — Architecture Documentation

Phase 1 architecture deliverables. All documents here describe the system design; implementation begins in Phase 2.

## Documents

| Document | Description |
|----------|-------------|
| [product-requirements.md](./product-requirements.md) | Product vision, user personas, feature goals, constraints |
| [functional-requirements.md](./functional-requirements.md) | Functional requirements summary by domain |
| [non-functional-requirements.md](./non-functional-requirements.md) | Performance, security, privacy, auditability NFRs |
| [system-architecture.md](./system-architecture.md) | Architecture overview, module map, technology choices |
| [database-design.md](./database-design.md) | Full schema: tables, columns, indexes, relationships |
| [api-specification.md](./api-specification.md) | REST API endpoints, request/response schemas, error codes |
| [ai-design.md](./ai-design.md) | LLM provider abstraction, three AI services, scoring engine algorithm |
| [security-and-privacy.md](./security-and-privacy.md) | Auth, RBAC, tenant isolation, file security, privacy controls |
| [ux-design-specification.md](./ux-design-specification.md) | Screen-by-screen UX design with states |
| [development-roadmap.md](./development-roadmap.md) | 10-phase implementation plan with dependencies and acceptance criteria |
| [architecture-decisions.md](./architecture-decisions.md) | Architectural Decision Records (ADRs) |

## Diagrams

| Diagram | Description |
|---------|-------------|
| [er-diagram.mmd](./er-diagram.mmd) | Entity-Relationship diagram (14 tables) — Mermaid format |
| [system-architecture.mmd](./system-architecture.mmd) | System deployment topology — Mermaid format |

## Key Architecture Decisions

1. **Modular monolith** — single FastAPI process, ARQ worker, shared PostgreSQL + Redis
2. **AI assists; humans decide** — AI extracts evidence; deterministic engine computes scores
3. **LLM provider abstraction** — swap providers via config; no business logic changes
4. **Protected attributes excluded at pipeline level** — PA stripping + runtime guard in scoring engine
5. **Audit log as transaction guard** — audit write failure rolls back the operation
6. **Scorecard and evaluation versioning** — full history retained; no destructive updates

## Requirements Document

The detailed EARS-format requirements with 30 requirements and 180+ acceptance criteria are in:

`.kiro/specs/shortlist-ai/requirements.md`

## Next Step

**Phase 2**: Set up monorepo structure, Docker Compose, SQLAlchemy models, Alembic migrations, FastAPI skeleton, JWT authentication, RBAC, and audit logger.
