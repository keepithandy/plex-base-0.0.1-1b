# P2-18b Literal Copy Continuation Result

## Status

**Complete and closed.**

The exact P2-18 v3 step-100 checkpoint was continued through cumulative step 500 in four isolated +100-update CUDA increments.

No training beyond step 500 was authorized or performed.

The final holdout remained closed.

## Learning curve

| Step | Training complete /144 | A /36 | B /36 | C /36 | D /36 | Tier A literal /18 | Tier B literal /18 | Tier C selected /18 | Tier D full /18 | Validation loss | Recent loss |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 100 | 4 | 2 | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 2.8767 | 0.5494 |
| 200 | 44 | 9 | 11 | 18 | 6 | 0 | 0 | 0 | 0 | 3.0392 | 0.2758 |
| 300 | 123 | 28 | 30 | 35 | 30 | 0 | 0 | 0 | 0 | 3.4574 | 0.1314 |
| 400 | 132 | 28 | 33 | 36 | 35 | 0 | 0 | 0 | 0 | 3.8189 | 0.0909 |
| 500 | 129 | 30 | 29 | 36 | 34 | 0 | 0 | 0 | 0 | 3.7898 | 0.0866 |

## Decisive finding

P2-18b produced a clean separation between supplied-task fitting and unseen literal transfer.

Training performance increased from **4/144** at step 100 to a peak of **132/144** at step 400.

Held-out exact literal performance remained **zero at every checkpoint**.

### Tier A — direct unseen literal copy

At steps 100, 200, 300, 400 and 500:

- complete: **0/18**
- literal exact: **0/18**
- selector exact: **0/9**
- value exact: **0/9**
- EOS: **18/18**

The simplest literal-copy primitive therefore failed to transfer even while the supplied curriculum became highly fitted.

### Tier B — labeled literal copy

At step 500:

- format valid: **18/18**
- label exact: **10/18**
- literal exact: **0/18**
- selector literal exact: **0/9**
- value literal exact: **0/9**

Plex transfers answer structure and some label behavior without transferring the arbitrary payload.

### Tier C — selected-field binding

Training Level C reached **36/36** by step 400 and remained **36/36** at step 500.

Held-out Tier C remained:

- selected-field exact: **0/18**
- wrong-field retrieval: **0/18**

This is important: Plex was not merely choosing the wrong contextual literal. It failed to reliably reproduce any unseen contextual literal.

### Tier D — three-field plan

At step 500:

- format valid: **7/18**
- selector exact: **0/18**
- old exact: **0/18**
- new exact: **0/18**
- full plan exact: **0/18**

Multi-literal plan assembly remains downstream of the same literal-reproduction bottleneck.

## Optimization behavior

Validation loss reached its best value at the original step-100 checkpoint and then worsened:

```text
100  2.8767
200  3.0392
300  3.4574
400  3.8189
500  3.7898
```

At the same time, recent training loss fell:

```text
100  0.5494
200  0.2758
300  0.1314
400  0.0909
500  0.0866
```

This is consistent with increasing specialization to the supplied mappings rather than improving held-out literal transfer.

## Development suites

P2-14 remained **0/12** throughout.

P2-01b remained **0/30** throughout.

EOS/stopping behavior remained strong, reinforcing the earlier finding that bounded completion transfers much earlier than coding semantics or arbitrary literal handling.

## Conclusion

P2-18/P2-18b is now closed.

Additional optimization on the unchanged literal-copy representation is **not justified**.

The result narrows the current bottleneck to arbitrary unseen-string reproduction/binding rather than CSS syntax, output formatting, stopping behavior, or simple supplied-task memorization.

## Next experiment

P2-19 tests **reference-mediated symbol binding**.

Instead of requiring the model to reproduce raw repository literals such as:

```text
.card-primary
18px
```

deterministic tooling can expose stable short references:

```text
R0
R1
R2
```

and ask the model to select or compose those references.

The critical diagnostic is whether Plex can generalize semantic reasoning over familiar reference tokens even when the underlying raw literals remain unseen.
