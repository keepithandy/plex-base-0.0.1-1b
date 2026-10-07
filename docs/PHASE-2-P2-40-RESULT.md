# P2-40 — Bridge Error Decomposition Result

## Status

**Diagnostic complete — October 7, 2026.**

P2-40 inspected the exact P2-39 response artifact without repairing, rescoring, or training.

## Result

The 18 development responses decomposed into:

- **9** invalid JSON responses
- **4** parseable JSON objects that violated the strict plan schema
- **5** schema-valid plans with semantic mismatches

Schema-valid coverage:

- HTML: **3 / 6**
- CSS: **1 / 6**
- JavaScript: **1 / 6**

Across the five schema-valid plans:

- language: **5 / 5 correct**
- action: **3 / 5 correct**
- targetKind: **5 / 5 correct**
- targetRole: **0 / 5 correct**
- exact constraints: **0 / 5**
- required hint coverage: **0 / 5**

## Structural failure

Thirteen outputs still fail before complete semantic-plan evaluation.

Observed failure modes include:

- duplicate JSON keys
- malformed key/value transitions
- missing required structured-plan fields
- malformed constraint objects
- field names and values partially substituted into neighboring fields

Plex therefore does not yet have reliable structured-plan serialization.

## Semantic failure

The five schema-valid outputs expose a separate and more important problem.

Plex consistently preserves the broad request category:

- language is correct in **5 / 5**
- targetKind is correct in **5 / 5**

But it does not bind the current request to the correct plan semantics:

- targetRole is **0 / 5**
- exact constraints are **0 / 5**
- required hint coverage is **0 / 5**

Representative substitutions include:

- an email-field task receiving disclosure-style semantics
- a CSS card-layout task receiving sticky/subnavigation semantics
- a USD-formatting task receiving aggregation/score semantics

This is evidence that Plex can recognize broad plan categories while still substituting familiar semantic bundles instead of deriving the target role, constraints, and hints from the current request.

## Comparison with P2-37

P2-37 classified the dominant failure as request-conditioned semantic binding / memorized concept collapse with residual serialization instability.

P2-38 changed the set of schema-valid outputs, but P2-39 did not improve the aggregate bridge gate and P2-40 shows that the underlying binding problem remains.

The failure is therefore not justified as a simple "train P2-38 longer" problem.

## Diagnosis

Primary failure:

**request-conditioned semantic binding / semantic-template substitution**

Secondary failure:

**residual JSON and strict-schema instability**

## Safety accounting

- training performed: **false**
- research optimizer updates: **0**
- final project holdout opened: **false**

## Decision

Do not extend the unchanged P2-38 training setup.

Proceed to **P2-41 — Request-Conditioned Plan Binding**, with structural serialization and semantic discrimination measured separately.

Machine-readable result:

`training/pretraining/p2-40-bridge-error-decomposition-result.json`
