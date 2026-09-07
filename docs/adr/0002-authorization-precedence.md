# ADR 0002: Deterministic controls outrank AI signals

- **Status:** Accepted
- **Date:** 2026-09-07

## Context

Intent alignment and injection detection can benefit from language models, but model results are probabilistic, may be unavailable, and may be influenced by adversarial content.

## Decision

Validated deterministic policies, session state, expiry, replay protection, and cryptographic checks are authorization controls. AI output is a bounded security signal and cannot override a hard failure or explicit deny.

## Consequences

- Unit tests can deterministically verify authorization behavior.
- Provider failure does not silently permit protected execution.
- Explanations must distinguish hard controls from probabilistic findings.

