# 2.1 — `amount` / `not_yet` event details and teacher amounts

**Status:** draft for Ashmita ACK (PLAN phase 2.1, issue #3).  
**Implements after ACK:** 2.2 (Arnav), 2.3 (simulator stubs).

## Goal

AB mode can compare fine state only when teacher and learner share a glasses viewpoint. Phase 2
emits two new learner events, `amount` and judged `not_yet`, with stable `detail` dicts for eval,
the simulator, and contract tests. Timed `not_yet` (from `Step.wait_s`) already exists; this spec
covers **amount** and **wait-until judgement**.

## Current code (unchanged semantics)

| Piece | Location |
|---|---|
| Event kinds | `src/instep/learner/events.py` |
| Timer `not_yet` | `StepMachine._timed_wait` — `detail.timer == true` |
| Lesson `Amount`, `WaitUntil` | `src/instep/lesson/schema.py` |
| Claims filter | `Lesson.claims()` — AB only for `amount` / `wait_until` |
| Labels | `LabelRow.kind` includes `amount`, `not_yet` |

## When events fire

### `amount`

- **Step:** current step has `step.amount` and `Claim.amount` is allowed.
- **Moment:** at **step completion** (same tick as `advance` for that step), after the object
  has met `completion` and before or with the advance (see ordering below).
- **Measure:** `learner_value = m.for_area(step.work_area).objects[amount.object].coverage` when
  `amount.measure == "work_area_fraction"` (only measure in schema v1).
- **Compare:** `teacher_value` and `tolerance` from the Lesson (filled by calibration on the
  teacher take; may already be set on hand-written Lessons).
- **Cue:** short, in the teacher's words. Wrong amount: corrective ("That's more than Maa used…").
  Within tolerance: optional praise or silence (default **no event** if within tolerance; see open
  decision).

### `not_yet` (judged)

- **Step:** current step has `step.wait_until`, `wait_until.still_checkable`, and
  `Claim.wait_until` is allowed.
- **Moment:** a **settle moment** (hands out of work area, motion below threshold, held
  `settle_s`), subject to existing `judge_every_s` / `min_step_s` guards, while the step is **not**
  complete.
- **Judge call:** same `StillJudge` as `end_state` progress, but prompt uses
  `wait_until.condition` and `wait_until.cue_not_yet` drives the spoken cue when `done == false`.
- **Not** used for `Step.wait_s` timer waits (those keep `detail.timer`).

### Event ordering (same `t_s`)

1. `amount` (if emitted)  
2. `advance` (if the step completes)  
3. `not_yet` / `stall` / etc. on later frames  

Eval treats same-second ordering as one window; labels use a single `t_s` per row.

## `detail` shapes (v1)

All keys are JSON-serialisable. Extra keys are allowed but ignored by eval v1.

### `amount`

```json
{
  "object": "mustard_seeds",
  "measure": "work_area_fraction",
  "learner_value": 0.14,
  "teacher_value": 0.08,
  "tolerance": 0.35,
  "ratio": 1.75,
  "within_tolerance": false
}
```

| Field | Type | Notes |
|---|---|---|
| `object` | string | `Amount.object` id |
| `measure` | string | Copy of `Amount.measure` |
| `learner_value` | number | Segmenter coverage at completion |
| `teacher_value` | number | From Lesson (calibrated) |
| `tolerance` | number | From Lesson |
| `ratio` | number | `learner_value / teacher_value` if `teacher_value > 0`, else `null` |
| `within_tolerance` | boolean | `abs(learner_value - teacher_value) <= tolerance * teacher_value` (relative band; see open decision) |

`Event.cue` carries what the learner hears. `step_id` is the completing step.

**Eval:** score `amount` rows where `within_tolerance == false` (learner used too much/too little).
Labels mark clearly wrong amounts; omit rows when the attempt was fine.

### `not_yet` (timer — already shipped)

```json
{
  "timer": true,
  "left_s": 42.5
}
```

No claim required (`needs_claim` returns `None`).

### `not_yet` (judged)

```json
{
  "timer": false,
  "condition": "the seeds start to pop",
  "judge_done": false,
  "visible": true,
  "confidence": 0.82,
  "missing": "seeds have not started popping yet"
}
```

| Field | Type | Notes |
|---|---|---|
| `timer` | boolean | Always `false` for judged path |
| `condition` | string | From `WaitUntil.condition` |
| `judge_done` | boolean | `StillVerdict.done` |
| `visible` | boolean | Work area visible enough to judge |
| `confidence` | number | From verdict |
| `missing` | string | From verdict; empty when `judge_done` |

Emit only when `judge_done == false` and `visible == true` (same as "not ready yet"). If not
visible, emit nothing (visibility is handled by `frozen` / stall logic).

`Event.cue` is `wait_until.cue_not_yet` (teacher wording), optionally trimmed if `missing` adds
specific detail (open decision).

### Claims and A'B

If `needs_claim(kind, detail)` is non-null and that claim is not in `lesson.claims()`, the event
must not be emitted (contract tests already pattern this for other kinds).

## Lesson schema tweaks (proposed)

Minimal change for 2.2:

### 1. `Amount.reference_frame_s` (optional)

```python
reference_frame_s: float | None = Field(default=None, ge=0)
```

Teacher still at the amount check, used in AB' on-screen callouts and optional judge context.
Hand-written Lessons may set it; **calibration** on the teacher replay sets it to the frame where
`teacher_value` was read if missing.

`WaitUntil.reference_frame_s` stays as today. `completion.reference_frame_s` stays for
`end_state` completion.

### 2. Calibration (no new top-level fields in v1)

Calibration run (2.2):

1. Replay teacher recording through `measure_clip` + `StepMachine` (same as learner).
2. For each step with `amount`, set `amount.teacher_value` from coverage at step end and set
   `amount.reference_frame_s` to that `t_s`.
3. For each `wait_until`, ensure `reference_frame_s` points at the teacher moment that satisfies
   the condition (human may edit after review).
4. Write updated Lesson JSON; bump nothing in `Calibration` unless we later store a hash of the
   teacher clip.

`teacher_value` on the hand-written Lesson remains the source of truth until calibration runs.

### 3. No new `measure` literals in v1

Keep `work_area_fraction` only. Count-based amounts ("two spoons") defer to a future
`measure: "count"` or judge-only check.

## Simulator (Ashmita, 2.3)

| Kind | Caption style | Spoken tone |
|---|---|---|
| `amount` | Accent color (e.g. purple), show `ratio` or plain words | Corrective, short |
| `not_yet` + timer | Muted, show countdown | Gentle wait |
| `not_yet` + judged | Distinct from timer (no countdown) | Teacher tip verbatim |

WebSocket payload unchanged: full `Event` objects including `detail`.

## Contract tests (2.2)

- Phone Lesson + amount on step → schema validation error (existing).
- Glasses Lesson + AB run → at least one judged `not_yet` and one `amount` on fixtures when
  machine logic is wired.
- A'B Lesson → replay never emits `amount` or judged `not_yet`.

## Open decisions (owner)

1. **Emit `amount` when within tolerance?** Proposal: **no** (less noise). Labels only mark wrong
   amounts.
2. **Tolerance math:** relative `tolerance * teacher_value` vs absolute band. Proposal: relative
   (matches fractional coverage).
3. **Cue enrichment:** use `missing` from judge to append to `cue_not_yet`, or cue field only.

---

**ACK checklist (Ashmita):**

- [ ] `amount` / judged `not_yet` `detail` tables above
- [ ] `Amount.reference_frame_s` added to schema v1
- [ ] Within-tolerance amount behaviour (open decision 1)
- [ ] Simulator cue presentation (2.3)