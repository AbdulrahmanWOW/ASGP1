# ADR 0001: Start as a modular monolith

- **Status:** Accepted
- **Date:** 2026-09-07

## Context

ASGP has several logical security layers, but the graduation MVP must be easy to run, test, debug, and demonstrate on one machine. Splitting each layer into a service would add deployment and consistency work before the security path is proven.

## Decision

The backend will begin as one FastAPI deployment with modules separated by responsibility. PostgreSQL will later provide durable state. The SDK and frontend remain separate packages because they run in different processes and have different consumers.

## Consequences

- Security-layer interfaces remain explicit and independently testable.
- One transaction can persist an action, decision, and audit event consistently.
- Deployment remains suitable for a graduation demonstration.
- A module may be extracted later only when measurements show a concrete need.

