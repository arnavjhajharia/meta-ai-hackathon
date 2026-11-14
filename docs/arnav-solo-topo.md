# Arnav-only subgraph (no Ashmita deliverables)

Ashmita-owned upstream work (recordings, hand AB Lesson, label confirm, Mock Kit app, etc.) is **excluded**. Chai task + Phase 0 reset are already done except the open “aim” bullet.

Topological order — do in this sequence; items with the same number can overlap.

## 1 — Phase 1 core (unblocks later eval once she lands footage)

1. **1.2** — A'B Lesson from chai tutorial `xTGYLBQr56k`: draft → `/lesson-review` → commit under `data/lessons/generated/`.
2. **1.2b** — Same pass: `finish()` wired through learner CLI/sim (heads-up if new event kind).
3. **1.2c** — Write the label-file strategy (one file per clip vs shared step ids) in PLAN or a short `docs/labels.md` so 1.8 is mechanical later.

## 2 — Interface specs (you draft; she ACKs when online — no footage)

4. **2.1** — `amount` / `not_yet` `detail` shape + any teacher-amount schema tweak (issue #3 checklist).
5. **5.1** — Per-frame `measure` contract for live path (vs clip hash today).
6. **6.1** — Voice Q&A API: question + Lesson + still → answer text.

## 3 — Offline engineering (still no her videos)

7. **5.2** — After 5.1: per-frame measure + segmenter benchmark (`gdino-sam2` vs SAM) on existing fixtures; pick live candidate without regressing phase-1 thresholds on synthetic/tutorial replays.
8. **6.2** — After 6.1: answer provider + tests with fake stills/Lesson (no glasses).
9. **2.2-prep** — After 2.1: implement `amount` + judged `not_yet` + contract tests; **calibration** on teacher take waits on **1.6** (her).

## 4 — Housekeeping

10. **P0** — Close “what we’re aiming for” (portfolio / users / next deadline) in PLAN.md.

---

## Frozen until Ashmita ships

| Step | Waiting on |
|------|------------|
| 1.7, 1.8, 1.10 | 1.3 recordings, 1.6 AB Lesson, 1.9 confirm |
| 2.2 calibrate, 2.5–2.6 | 1.3, 1.6, label confirm |
| 3.2 | 2.2 calibrate + 3.1 glasses teacher |
| 7.1 (eval numbers) | 2.6 |

Visual subgraph: `task-graph.html` → toggle **Solo mode**.