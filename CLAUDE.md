# InStep

Record once, anyone can learn it.

So much of what people know how to do lives only in their hands: a parent's recipe, a
technician's fix, a craft passed down in a family. InStep lets a teacher do a task once while
being recorded, understands what they did (including the small things they never say out
loud), and turns it into a lesson someone else can follow, either as a watchable tutorial or
live through Meta Ray-Ban glasses that watch the learner's hands.

This is our entry for the Meta Global AI Developer Hackathon, Indie track. Two builders,
submissions due **Nov 4, 9 PM ET**. Judged on Impact 30%, use of Meta AI tooling 25%,
Demo 25%, Technical depth 20%. Every decision should serve a live demo that works on stage.

## Vocabulary

Two variables describe every way InStep works:

| | wears the glasses | uses a phone |
|---|---|---|
| Teacher | **A** | **A'** |
| Learner | **B** | **B'** |

| Mode | Meaning | What InStep produces |
|---|---|---|
| **AB** | glasses to glasses | A live lesson on the learner's glasses, checked against the teacher's own point of view. Same viewpoint means we can judge amounts and "wait until" moments. |
| **AB'** | glasses to phone | An edited, watchable tutorial from the teacher's unedited first-person recording: dead time cut, steps found, tips kept. |
| **A'B** | phone to glasses | A live lesson on the glasses from an ordinary filmed tutorial. Different viewpoints, so only coarse checks (presence, order, progress). |
| A'B' | phone to phone | That is just a video. Out of scope. |

Use these names in code, commits, tests and conversation.

## Current focus

> Edit this section at the start of each session. Everything else in this file is stable.

**Today: B is fixed (the learner wears glasses). We build AB and A'B.**

Glasses footage is hard to get, so the teacher side is split:
- **A (glasses teacher)**: not built today. We hand-write a few Lessons as if a glasses teacher
  made them (`authored: hand_written`), with amounts and "wait until" steps.
- **A' (phone teacher)**: built for real, nothing hand-written. A YouTube tutorial goes in and a
  Lesson comes out (Whisper, then one Claude pass, then SAM snaps step times). Coarse claims only.

Done for today means:
1. A written, versioned Lesson schema (the contract every other part reads and writes).
2. **A'B**: a YouTube tutorial goes in and a Lesson comes out (steps, objects to track, tips in
   the teacher's words, step times snapped by the segmenter).
3. **B**: a learner attempt (Arnav, phone strapped at the chest) runs against both a hand-written
   AB Lesson and the A'B Lesson and produces the right events (advance, skip, stall, and for AB
   only amount and not yet) on at least one labelled clip.
4. A web glasses simulator replays the attempt in real time with captions and spoken cues. It
   reads frames through a `FrameSource`, so Meta's Mock Device Kit plugs in later.

Use one task for all three (tutorial, hand-written Lesson, attempts) so one attempt tests both
modes.

Not today: building the A pipeline, AB', the phone app, voice questions.

YouTube tutorials are for development only; the demo uses our own recordings. Chest-phone
recordings are stand-ins for glasses: mark them in their filenames.

## The Meta stack and today's stand-ins

| Meta role | What it does for us | Stand-in until credits arrive | Notes |
|---|---|---|---|
| Ray-Ban glasses | First-person video (720p stream, high-res stills), mics, open-ear speakers, via the Wearables Device Access Toolkit | Recorded footage; Mock Device Kit for app work | Audio streaming and photo capture are experimental in the toolkit |
| Muse Spark | Understands the whole teacher recording in one pass (1M context, takes video); judges "wait until" moments from stills | Claude via the Anthropic API | Meta Model API is OpenAI-compatible (api.meta.ai/v1) |
| SAM 3.1 | Finds and tracks hands and objects from text prompts | SAM 3 on a Modal GPU, or on the Mac (slow) | Hosted sam-3.1 exists on Meta Model API |
| Muse Voice Transcribe | Teacher narration, learner speech | Local Whisper | No open weights, API only |

**Every vendor SDK lives behind one interface per role.** Swapping a stand-in for the Meta
service must be a config change, never a code change elsewhere. Tests always run on fake
providers with no network and no GPU.

## Design principles

These are the decisions that make InStep technically deep rather than a demo trick. Keep them
true as the code changes.

1. **One Lesson, many outputs.** Every mode reads the same Lesson. A Lesson records how it was
   made (teacher on glasses or on a phone) so downstream code knows what it can trust.
2. **Claims follow the recording.** Compare amounts and fine states only when teacher and learner
   share a viewpoint (AB). From a phone on a stand (A'B), stick to presence, order and progress.
3. **Fast path and slow path.** Segmentation runs on every sampled frame and drives all timing.
   The reasoning model is called rarely: once per teacher recording, and on single stills at the
   moments that need judgement. Never put a reasoning model in the per-frame loop.
4. **The teacher is the first learner.** The model's step times from sparse keyframes are rough.
   Replaying the teacher's own recording through the same machinery the learner uses snaps them
   to what actually happened and records the teacher's amounts.
5. **Not seeing is not evidence.** When the work area is out of view (the wearer looked away),
   freeze; never treat it as empty, finished or stalled.
6. **Cache everything that costs money or minutes.** Segmentation and model calls are cached by
   their exact inputs, so re-running evals while tuning logic is free.

## How we work

- **Plan before code.** For anything bigger than a small fix, use plan mode: propose the
  approach, the files, and how we will know it works. Wait for a yes.
- **Contracts first.** Write or update the schema and the test that pins it down before the code
  that produces it.
- **Measure, don't assert.** Each learner-side behaviour is scored against hand-made labels.
  Run the eval before and after any change to detection logic or thresholds and show both results.
  A clip that passed before and fails now is a regression: fix it or explain it.
- **Give yourself eyes.** For any video or visual output, render something you can open with the
  Read tool (a timeline plot of what was detected over time, a grid of frames with masks drawn on)
  and look at it before reasoning about why something failed. For any web page, open it with the
  Playwright MCP at 390x844 and screenshot it.
- **Never grade your own homework.** Do not create or edit labels, or the scoring code, to make
  something pass. Draft labels for a human to confirm; never commit them unconfirmed.
- **Small commits** with the mode in the message, e.g. `AB': cut dead time between steps`.

## Tooling in this repo

Use these instead of improvising the same workflow each time.

| Skill (`/name`) | When |
|---|---|
| `lesson-review` | Every time a Lesson is created or changed, before anything uses it |
| `look` | Before explaining or tuning any detection result: render it, then read the images |
| `eval` | Any change to detection logic, thresholds, calibration or prompts |
| `label` | A new learner recording needs labels (human confirms every row) |
| `phone-preview` | Before calling any web page done (the AB' player first) |
| `meta-stack` | Writing provider code, estimating cost, kickoff-day swaps |
| `gpu-budget` | Before any Modal deploy, run, or batch segmentation |

Subagents: `frame-critic` (independent read of the images when a theory has already formed) and
`docs-scout` (fetch official docs instead of guessing an API; keeps long docs out of context).
MCP: Playwright, for screenshots. Hooks format Python after every edit and stop a turn from
ending while lint or tests are red.

Add a new skill only when the same instructions have been typed twice. Keep this file for rules
that apply every turn; put procedures in skills.

## Money and credits

- Anthropic credits: fine for development, but every call goes through the cache. Ask before any
  command that makes more than a handful of uncached model calls.
- Modal: **$30 total**. L4 GPU only (about $0.80/hour) unless told otherwise. Ask before
  `modal deploy` or `modal run`. Never keep a container warm. After any session that used Modal,
  run `modal app list` and confirm nothing is still running. Report estimated spend.
- Meta credits are not here yet. Do not write code that assumes them.

## Team and data reality

- Arnav (India) has no glasses and develops entirely against recorded footage.
- The teammate (Canada) has the glasses, builds the phone app, and records teacher sessions and
  learner attempts.
- Recordings live in `data/recordings/`, hand labels in `data/labels/`. Videos are not committed.
- Synthetic test footage is useful for plumbing and regression tests, but it is far cleaner than
  reality. Never tune thresholds on synthetic data.

## Conventions

- Python 3.12 in a local virtual environment (`.venv`); never install into system Python.
- `ruff` for formatting and linting, `pytest` for tests, type hints on public functions.
- Fake providers in every test. No test touches the network, a GPU, or a paid API.
- Secrets only in `.env` (never read it, never commit it). Config via environment variables.

## Words people hear or read

Spoken cues, tips, tutorial text, README and demo copy: plain, warm, short, in the teacher's voice
where possible ("Not yet. Maa waited until the seeds started to pop."). Never use em dashes.

## Commands

> Fill this in as commands come into existence. Keep it accurate; delete anything that stops working.

- Install: `.venv/bin/python -m pip install -e '.[dev]'`
- Tests: `.venv/bin/python -m pytest -q`
- Lint: `.venv/bin/ruff check . && .venv/bin/ruff format --check .`
- Regenerate the Lesson JSON Schema after changing `src/instep/lesson/schema.py`:
  `.venv/bin/python -m instep.lesson.io` (a test fails if `schemas/lesson.v1.json` is stale)
