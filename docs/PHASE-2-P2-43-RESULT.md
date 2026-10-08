# P2-43 — Semantic Bundle Reuse Diagnostic Result

## Result

**P2-43 is complete.**

The diagnostic confirms that P2-41 substantially improved JSON/schema serialization, but unseen semantic binding remains dominated by training-template retrieval.

The fixed P2-42 response set contained:

- **18** responses
- **17 / 18** strict schema-valid plans
- **0 / 18** complete semantic passes
- language correct: **17 / 18**
- action correct: **12 / 18**
- targetKind correct: **17 / 18**
- targetRole correct: **0**
- exact constraints: **0**
- required hint coverage: **0**

Compared with P2-39, schema validity improved by **12 responses**.

## Training-template reuse

Among the 17 strict plans:

- **14** emitted a targetRole that existed in the P2-41 training split
- **11** reused an exact P2-41 training constraint set
- **13** reused exact P2-41 training search hints
- **8** reused an exact P2-41 training semantic bundle
- **7** reproduced an exact P2-41 training full plan
- **2** recombined semantic components that were individually present in P2-41 training but did not belong to one exact training bundle

No validation-only role or semantic bundle was reused.

The diagnostic classifications were:

- **8** wrong plans with an exact P2-41 training semantic bundle
- **6** wrong plans with a P2-41 training targetRole
- **3** wrong plans with a novel role/bundle shape
- **0** semantic passes

Repeated collapse included:

- `p241-pricing-table-target`: **3 outputs**
- `p241-score-average-target`: **2 outputs**

## Interpretation

This is stronger than ordinary noisy transfer.

Plex is not merely producing plans that look like P2-41. A large share of the wrong outputs contain semantic identities and bundles that were directly exposed during P2-41 gradient training.

The clearest evidence is that **14 of 17 strict outputs use a training-seen targetRole while targetRole correctness remains zero**. Exact P2-41 full plans appear in **7 of 17** strict outputs, and exact semantic bundles appear in **8 of 17**.

At the same time, validation-only reuse is zero.

That pattern supports this diagnosis:

> P2-41 taught Plex a strong structured-plan prior and a library of semantic templates, but did not teach reliable request-conditioned composition of targetRole, constraints, and search hints.

Serialization is therefore no longer the primary bottleneck.

## Training decision

Do not continue optimization on the unchanged 108-record P2-41 curriculum.

P2-41 already reached a very low training loss while P2-43 shows that the remaining unseen errors are dominated by training-template retrieval and component recombination. More updates on the same examples would risk strengthening that behavior.

## Next milestone

**P2-44 — Evidence-First Semantic Composition**

P2-44 will keep the production structured-plan schema but redesign the curriculum so that:

- targetRole is derived from request-supported semantic atoms
- constraints come from explicit request requirements
- search hints are grounded in request wording
- opaque `p241-*`-style semantic identifiers are prohibited
- individual semantic atoms may be familiar, but validation requires **novel combinations**
- exact train/validation semantic-bundle reuse is prohibited

P2-44 begins as a zero-update design and curriculum-review milestone.

## Safety accounting

- training performed: **false**
- optimizer updates: **0**
- checkpoint selection: **none**
- response repair: **none**
- final holdout: **closed**
