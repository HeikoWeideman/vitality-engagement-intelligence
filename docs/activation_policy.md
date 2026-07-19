# Stage 5 Activation Policy Contract

## Status

Stage 5.1 defines the activation policy and typed contracts only. It does not select members,
write activation artifacts, write to BigQuery, or deliver interventions.

## Intended use

The activation pipeline converts verified engagement-risk forecasts into supportive,
human-reviewed recommendations. It must not be used to deny benefits, change eligibility,
penalise members, make clinical or diagnostic conclusions, infer real health status, or claim
causal intervention effects.

All current data is synthetic. Operational scoring rows are forecasts and are not confirmed
missed-goal outcomes.

## Source contract

The source is the verified Stage 4 scoring artifact with these fields:

- `member_id`
- `prediction_date`
- `risk_probability`
- `is_high_risk`
- `model_name`
- `threshold`

The frozen logistic threshold remains `0.431`. The activation layer may not alter or retune it.

## Stage 5 development policy

The initial deterministic development policy uses:

- High-risk predictions only
- Maximum prediction age of 7 days
- Contact cooldown of 7 days
- Maximum 2 interventions per member in 28 days
- Maximum 100 selected activations per run
- Mandatory human review
- Supportive use only

These are engineering defaults for a synthetic portfolio project, not validated clinical,
behavioural, legal, or production operating rules. Changing them requires a new policy version.

## Decision order

The future decision engine will apply this order:

1. Validate the scoring row and frozen-threshold classification.
2. Retain one latest prediction per member using deterministic ordering and audit older rows
   as superseded no-contact decisions.
3. Record below-threshold rows as no-contact outcomes.
4. Apply exclusions: missing context, contact not permitted, then member opt-out.
5. Apply suppressions: stale prediction, active case, contact cooldown, then prior-contact limit.
6. Rank remaining eligible members by risk probability descending, prediction date descending,
   and member ID ascending as the stable tie-breaker.
7. Apply the per-run capacity limit.
8. Produce supportive recommendations for human review only.
9. Write one audit outcome for every input scoring row.

Stage 5.3 will implement and test this ordering. Stage 5.1 only freezes its contract.

## Deterministic run identity

A run ID is derived from:

- Full policy fingerprint
- Model name
- Frozen threshold
- Scoring artifact SHA-256 digest
- Exact timezone-aware decision timestamp, normalised to UTC

Re-running the same governed inputs at the same decision timestamp produces the same run ID. A change to any governed input
produces a different ID.

## Typed records

The source code defines typed contracts for:

- Scored prediction
- Member activation context
- Eligible prediction
- Excluded prediction
- Suppressed prediction
- Intervention recommendation
- Selected activation
- Activation audit record
- Activation run metadata

Raw dictionaries are not the primary application interface.

## No-contact outcomes

No-contact decisions are explicit audit outcomes rather than missing records. Reasons include:

- Superseded by the latest member prediction
- Below frozen threshold
- Missing activation context
- Contact not permitted
- Member opted out
- Prediction too old
- Active case open
- Contact cooldown active
- Prior intervention limit reached
- Capacity limit reached

## Deferred work

This milestone deliberately defers:

- Deterministic eligibility and ranking implementation
- Activation Parquet and metadata writers
- BigQuery activation tables or merge logic
- Dashboard development
- Intervention delivery or message sending
- Experimental treatment assignment
