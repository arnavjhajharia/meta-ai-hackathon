# InStep plan

The full vision, in phases. Each phase has an owner, what "done" means, and how we check it.
Read `CLAUDE.md` for vocabulary (A, A', B, B', AB, AB', A'B) and design principles.
`HACKATHON.md` is history from the event; its demo outline is still useful for phase 7.

## Who owns what

Two lanes, split along code boundaries so we rarely touch the same files. Each lane is mostly
dev work; recording is a side job for Ashmita because she has the glasses.

| | **Arnav**: understanding and detection | **Ashmita**: capture, delivery and product |
|---|---|---|
| In one line | What happened in a recording, and was it right | Getting frames in, getting lessons and cues out to people |
| Owns | `teacher/`, `learner/`, `eval/`, the understander, judge and segmenter providers | `sources/`, `sim/`, the phone app, the live backend, AB' rendering and player, voice |
| Modes | A, AB, A'B detection | AB', the live loop for every mode |
| Also | Eval numbers, prompts, thresholds, credit spend | Recordings, hand-written AB Lessons, confirming labels, README, demo video |

Shared contracts: `lesson/schema.py` and `learner/events.py`. Changing either needs a heads up to
the other person and the contract test updated in the same commit.

**Never grade your own homework, across lanes:** Arnav drafts labels and Ashmita confirms them, so
the person tuning detection is never the one who signs off the ground truth.

## Where we are (Nov 12)

All work so far is from kickoff day (Oct 26). The hackathon is over (the Nov 4 deadline has
passed) and **we no longer have Meta credits**: no Muse Spark, no hosted SAM 3.1, no Muse Voice
Transcribe. We keep building for ourselves on Anthropic credits plus local models. The glasses
and Meta's free developer tools (Wearables Device Access Toolkit, Mock Device Kit) need no
credits and stay in the plan.

Built:
- Lesson schema v1 with provenance and claims (`lesson/schema.py`, `schemas/lesson.v1.json`).
- A'B teacher pipeline: Whisper, one Claude draft (prompt v3), quote grounding, SAM calibration.
- Learner state machine: advance, skip, stall, frozen/resume, timed waits, judge at settle moments.
- Providers behind one interface per role, fakes for tests, a cache, and a spend log.
- CLI, timeline and overlay renders, and a web glasses simulator.

Missing:
- No Lessons committed (`data/lessons/hand/` and `data/lessons/generated/` are empty).
- No labels and no eval numbers.
- `amount` and judged `not_yet` events are never emitted, so AB is really A'B plus timers.
- `StepMachine.finish()` does nothing.
- `FrameSource` is defined but not used anywhere.
- Nothing for A, AB', the live loop, voice, the README or the demo video.

## How the phases fit

```
0 Reset ──> 1 Close day 1 ──> 2 AB checks ──┐
                    │                       ├──> 5 Live loop ──> 6 Voice ──> 7 Demo
                    └──> 3 A pipeline ──> 4 AB'
Recording (Ashmita) runs alongside everything from phase 1 on.
```

The old Meta swap phase is gone: there are no Meta credits. The only paid service is the Anthropic
API (see "Models and credits" below); everything else runs locally.

Run the lanes in parallel:

| Phase | Arnav | Ashmita |
|---|---|---|
| 1 | A'B Lesson, `finish()`, label drafts, eval baseline | `FrameSource` wiring, hand-written AB Lesson, learner recordings, label confirmation |
| 2 | Amounts and judged not-yet | Simulator shows the new events; start the phone app on Mock Device Kit |
| 3 | A pipeline | Teacher recordings |
| 4 | Supplies calibrated spans | All of AB' |
| 5 | Fast-path latency, segmenter speed | Device source, app, live backend, spoken cues |
| 6 | Answer quality | Voice pipeline end to end |
| 7 | Eval numbers, architecture diagram | Video, README, rehearsals |

### Who waits on whom

Each phase below ends with an **Order** table: the steps where one of us blocks the other,
numbered by phase (1.3 is phase 1, step 3). A step with nothing under "waits on" can start right
away. **Agree** steps are short conversations that settle a shared interface, so both sides can
build in parallel against fakes.

The long pole is 1.3 (Ashmita's recordings): 1.6 to 1.10, 2.2 and 2.5 all wait on it. Record
first.

Files neither lane owns, so pull before editing and keep commits small: `cli.py`,
`sim/server.py` (Arnav reads it, Ashmita changes it), `providers/registry.py`.

Rubric reminder: Impact and Demo are 55%. One mode that works every time beats three shaky ones.
If time runs short, ship phases 1, 2 and 7 with AB as the lead, and cut 4 or 6 before cutting
the eval.

---

## Phase 0: Reset (both, short)

- [x] Make a fresh `.venv`, `pip install -e '.[dev]'`, tests and lint green.
- [ ] Decide what we are aiming for now (a later hackathon, a portfolio piece, real users).
- [x] Write the Anthropic credit balance into "Models and credits" below and set
      `INSTEP_SPEND_CAP_USD` to match.
- [x] One real (uncached) Opus draft on the chosen tutorial to replace the cost estimates below
      with a measured number from `.cache/spend.jsonl`.
- [x] Update "Current focus" and the Meta stack table in `CLAUDE.md` to point at this file.

**Done when:** `pytest -q` and lint pass on a clean checkout, and the credit balance, the cap and
one measured draft cost are written down.

## Phase 1: Close day 1, A'B and B on recorded footage (both)

Pick **one task** for everything (masala chai fits the story; the paper boat is easier to see).
Use the same task for the tutorial, the hand-written Lesson and the learner attempts.

Arnav:
- [ ] Generate the A'B Lesson from the chosen tutorial, run `/lesson-review`, commit it to
      `data/lessons/generated/`.
- [ ] Draft labels for the learner clips with `/label`.
- [ ] Run `/eval` against both Lessons and record baseline numbers in `runs/` and in this file.
- [ ] `finish()`: emit a final event when the recording ends partway through (unfinished step).

Ashmita:
- [ ] Record two or three learner attempts of the chosen task (chest phone stand-in is fine, mark
      it in the filename). Between them: a deliberate skip, a stall, a clearly wrong amount, and
      reaching in too early on a "wait until" step (phase 2 needs the last two).
- [ ] Record one teacher take of the same task. The AB Lesson's reference frames and the
      teacher's amounts come from it.
- [ ] Hand-write the AB Lesson (`authored: hand_written`) with at least one amount and one
      "wait until" step, run `/lesson-review`, commit it to `data/lessons/hand/`.
- [ ] Confirm every label row Arnav drafted, then commit them to `data/labels/`.
- [ ] Add a file `FrameSource` in `sources/` and wire it into `sim/server.py` and `cli learn`, so
      nothing reads video files directly except that source. Tests on a tiny synthetic clip.

Order:

| # | Who | Step | Waits on |
|---|---|---|---|
| 1.1 | Both | Pick the one task (chai or paper boat) | |
| 1.2 | Arnav | A'B Lesson from the tutorial; `finish()` (heads up if it adds an event kind) | 1.1 |
| 1.3 | Ashmita | Learner attempts (skip, stall, wrong amount, early reach) and one teacher take | 1.1 |
| 1.4 | Both | **Agree** how a `FrameSource` gives `measure_clip` a cache key | |
| 1.5 | Ashmita | File `FrameSource`, wired into the simulator and `cli learn` | 1.4 |
| 1.6 | Ashmita | Hand-write the AB Lesson, reference frames pointing at the teacher take | 1.3 |
| 1.7 | Arnav | `/lesson-review` on the AB Lesson: objects the segmenter can find, sensible completions | 1.6 |
| 1.8 | Arnav | Draft labels for the learner clips | 1.3 |
| 1.9 | Ashmita | Confirm every label row | 1.8 |
| 1.10 | Arnav | Eval baseline against both Lessons | 1.2, 1.7, 1.9 |

**Done when:** `/eval` prints per-event precision and timing error for both Lessons on the
labelled clips, and the simulator replays a clip through a `FrameSource`.

## Phase 2: AB checks, amounts and "wait until" (Arnav)

The checks only AB can make, because teacher and learner share a viewpoint.

- [ ] Teacher as first learner records amounts: when calibrating an AB Lesson, store the
      teacher's measured coverage or count for each `Amount` step, plus a reference still at the
      moment the step ends.
- [ ] `amount` event: compare the learner's measure with the teacher's at the moment the step
      completes; cue in the teacher's words ("That's more than Maa used. About two spoons.").
- [ ] Judged `not_yet`: on a `WaitUntil` step, at a settle moment, ask the judge with the
      learner still and the teacher's reference still; cue the teacher's own tip.
- [ ] Contract tests: these events are dropped for A'B Lessons (claims filter), emitted for AB.
- [ ] Draft labels for the amount and not-yet moments (Ashmita confirms); run `/eval` before and
      after.

Ashmita, in parallel:
- [ ] Simulator shows `amount` and `not_yet` cues distinctly (caption style, spoken tone).
- [ ] Start the phone app against Meta's Mock Device Kit: connect, stream frames, show them.

Order:

| # | Who | Step | Waits on |
|---|---|---|---|
| 2.1 | Both | **Agree** the `detail` shape of `amount` and `not_yet`, and any schema change for teacher amounts | |
| 2.2 | Arnav | Amounts and judged not-yet; calibrate on the teacher take | 1.6, 2.1 |
| 2.3 | Ashmita | Update the AB Lesson if the schema changed; simulator shows the new events (stubbed until 2.2) | 2.1 |
| 2.4 | Ashmita | Phone app on Mock Device Kit | |
| 2.5 | Arnav, then Ashmita | Draft, then confirm, amount and not-yet labels on the 1.3 clips | 1.3 |
| 2.6 | Arnav | Eval with the new events, before and after | 2.2, 2.5 |

**Done when:** on at least one labelled AB clip, `amount` and `not_yet` fire at the right moments
with no regressions on phase 1 numbers.

## Phase 3: A pipeline, glasses teacher to Lesson (Ashmita records, Arnav builds)

Replaces the hand-written AB Lessons with real ones.

- [ ] **Ashmita:** record two or three real teacher sessions on the glasses, talking it through.
      Ideally a real parent for the demo task.
- [ ] Understander (Claude Opus) reads the whole recording in one pass as keyframes plus the
      transcript (Claude takes images, not video). Output is the same DraftLesson the A' path
      makes, plus amounts and "wait until" moments.
- [ ] Provenance `teacher_device: glasses`, so `claims()` includes amount and wait_until.
- [ ] Calibrate by replaying the teacher's own recording through the learner machinery (phase 2
      fills in the amounts and reference stills).
- [ ] `/lesson-review` on each generated Lesson; diff against the hand-written one for the same
      task.

Order:

| # | Who | Step | Waits on |
|---|---|---|---|
| 3.1 | Ashmita | Teacher sessions on the glasses | |
| 3.2 | Arnav | A pipeline: glasses recording to a calibrated AB Lesson | 2.2, 3.1 |

**Done when:** a learner clip scores at least as well against the generated AB Lesson as against
the hand-written one.

## Phase 4: AB', glasses recording to a watchable tutorial (Ashmita)

Reads only a calibrated Lesson and the recording, so it needs nothing from Arnav beyond phase 3.
New code goes in its own module (`src/instep/tutorial/`).

- [ ] Cut dead time: keep each step's calibrated span plus padding; drop spans with no hands in
      the work area and no speech.
- [ ] Chapters from the steps, tips as captions in the teacher's words, amounts shown on screen.
- [ ] Render with ffmpeg (no new dependency) to an mp4 plus a chapter JSON.
- [ ] A phone player page (chapters, captions, replay step). Run `/phone-preview` at 390x844.
- [ ] Check: someone who has not seen the raw footage follows the tutorial and completes the task.

Order:

| # | Who | Step | Waits on |
|---|---|---|---|
| 4.1 | Ashmita | AB' prototype on the A'B Lesson or the 1.3 teacher take, so no waiting | |
| 4.2 | Ashmita | AB' on a real glasses Lesson | 3.2, 4.1 |

**Done when:** a 10 to 20 minute raw recording becomes a 2 to 4 minute tutorial, and one stranger
gets through it.

## Phase 5: Live loop on the glasses (Ashmita leads, Arnav on the fast path)

Ashmita:
- [ ] Device `FrameSource`: Mock Device Kit first, then the real Wearables Device Access Toolkit
      720p stream, both through the same interface the simulator uses.
- [ ] Live backend: grow `sim/server.py`'s websocket into a server that takes frames from the
      phone, runs measure plus `StepMachine`, and sends events back.
- [ ] Phone app sends sampled frames and plays spoken cues through the glasses' open-ear
      speakers (phone TTS to start).

Arnav:
- [ ] Latency budget: frame to cue under about 1 s on the fast path. Measure it, show it.
- [ ] Segmenter speed: SAM 3 on the Mac is about 5 s a frame, too slow for live. Measure the
      `gdino-sam2` fallback and a smaller detector against `/eval`; pick the fastest one that
      holds the phase 1 numbers. No paid GPU.

Order:

| # | Who | Step | Waits on |
|---|---|---|---|
| 5.1 | Both | **Agree** a per-frame measure call for live use (the simulator measures whole clips today) | |
| 5.2 | Arnav | Per-frame measure; a segmenter fast enough for live; per-frame timing offline | 5.1 |
| 5.3 | Ashmita | Device `FrameSource`, live backend on the fake segmenter, cues on the glasses | 2.4, 5.1 |
| 5.4 | Both | Plug 5.2 into 5.3; Arnav measures frame to cue end to end | 5.2, 5.3 |

**Done when:** a learner wearing the glasses completes the demo task live, hearing cues, with the
lesson waiting, replaying and catching a skip.

## Phase 6: Voice questions (Ashmita leads, if time)

- [ ] Ashmita: learner asks a question ("how much salt?") through the glasses mic; transcribe with
      local Whisper; speak the answer back.
- [ ] Arnav: answer from the Lesson (tips, amounts) plus the current still, in the teacher's voice.
- [ ] Ashmita: replay the teacher's clip for that step when that helps more than words.

Order:

| # | Who | Step | Waits on |
|---|---|---|---|
| 6.1 | Both | **Agree** the answer interface (question, Lesson, still in; text out) | |
| 6.2 | Arnav | Answer quality | 6.1 |
| 6.3 | Ashmita | Voice pipeline on a fake answerer, then the real one | 5.3, 6.1 |

**Done when:** three scripted questions get correct, short answers during a live run.

## Phase 7: Demo and submission (both)

- [ ] Ashmita: script the video from the outline in `HACKATHON.md` (best moment in the first 30 s).
- [ ] Ashmita: record with a real teacher and a real learner, lead with AB.
- [ ] Arnav: eval numbers on screen (step timing, skip, amount, not-yet) and the architecture
      diagram.
- [ ] Ashmita: README covering what it is and how to run the simulator on a recorded clip.
- [ ] Both: clean repo with no secrets and no videos, runnable from a fresh clone.
- [ ] Both: rehearse the live demo end to end twice, with a recorded fallback ready.

Order:

| # | Who | Step | Waits on |
|---|---|---|---|
| 7.1 | Arnav | Final eval numbers and architecture diagram | 2.6 |
| 7.2 | Ashmita | Video script, recording, README | 5.4, 7.1 |
| 7.3 | Both | Clean repo, rehearse the live demo twice | 7.2 |

**Done when:** the video is uploaded, the README runs on a fresh clone, and the live demo has
gone right twice in a row.

---

## Models and credits (Anthropic only)

There are no Meta services and no Modal. Claude through the Anthropic API is the only thing that
costs money; segmentation, speech and voice run on the Mac. Every provider stays behind its
interface in `providers/`, so a different model later is still a config change.

| Role | Model | Where | Config |
|---|---|---|---|
| Understander (recording to DraftLesson, once per recording) | Claude Opus 5.5, effort `high` | Anthropic API | `INSTEP_DRAFT_MODEL`, `INSTEP_DRAFT_EFFORT` |
| Still judge ("wait until", amounts, settle moments) | Claude Sonnet 5.5; try Haiku 5.5 | Anthropic API | `INSTEP_JUDGE_MODEL` |
| Voice answers (phase 6) | Claude Sonnet 5.5 or Haiku 5.5 | Anthropic API | new provider, same pattern as the judge |
| Segmenter (every sampled frame) | SAM 3 fp16; `gdino-sam2` fallback | Mac (MPS) | `INSTEP_SEGMENTER` |
| Transcriber | Whisper large-v3-turbo (MLX) | Mac | `INSTEP_TRANSCRIBER` |
| Spoken cues | Browser speech synthesis (macOS `say` for renders) | Mac / browser | none |

Claude never sees video and never runs per frame (design principle 3). It gets keyframe grids plus
the transcript once per recording, and single stills at the few moments that need judgement.

### Where the credits go

The draft cost is measured (Nov 13, chai tutorial `xTGYLBQr56k`, prompt v3, 120 frames at
512 px plus a Hindi transcript: 22.1K input, 4.8K cache write, 6.2K output tokens, 55 s). The
other rows are still estimates; replace them from `.cache/spend.jsonl` as they get measured.

| Use | Calls | Estimated cost |
|---|---|---|
| Draft one Lesson (Opus, about 120 frames plus transcript) | 1 per recording, then cached | **$0.24 measured** |
| All Lessons we expect (10 tutorials, a few prompt revisions, 3 to 5 teacher recordings) | about 30 to 40 | about $7 to $10 |
| Judge on one learner attempt (Sonnet, 2 stills a call) | a few per attempt | a few cents per attempt |
| Eval reruns while tuning thresholds | cached unless a prompt or model changes | about $0 |
| Live demo and rehearsals (judge plus voice) | tens per run | under $1 per run |

Credit balance: **$50**, and the spend cap is set to match. Spend so far: $0.24 (one draft,
Nov 13). Earlier drafts were written by Claude Code subagents through `prepare` / `ingest`.

### Rules

- Every call goes through the cache, keyed by its exact inputs. Never bypass it in a script.
- `INSTEP_SPEND_CAP_USD` (default $50) is checked against the total in `.cache/spend.jsonl`
  before each call; raise it on purpose, never to get one run through.
- Ask before any command that makes more than a handful of uncached calls (a prompt change that
  invalidates every Lesson, a batch over all tutorials).
- Model or effort changes are eval changes: run `/eval` and `/lesson-review` before and after,
  and log both here.
- A prompt revision is drafted on one tutorial first, reviewed, and only then rerun on the rest.
- Use the subagent path (`prepare`, then a subagent drafts, then `ingest`) for exploratory prompt
  work; it costs no API credits.
- Try Haiku 5.5 as the judge once phase 2 has labels. Keep it only if the not-yet and amount
  numbers hold.

---

## Risks

| Risk | What we do |
|---|---|
| Glasses footage is slow to get | Chest-phone stand-ins for phases 1 and 2; hand-written AB Lessons until phase 3. |
| Anthropic credits run out | Spend cap plus cache; subagent drafting for prompt work; Haiku judge if it holds up in the eval. |
| SAM too slow for live use | Lower the sampling rate; `gdino-sam2` or a smaller detector; fall back to the recorded demo with the simulator. |
| Thresholds tuned on too few clips | At least two labelled clips per behaviour; never tune on synthetic footage. |

## Eval log

Record numbers here after every `/eval` run that changes detection.

| Date | Change | Clips | Advance timing (median s) | Skip P/R | Amount P/R | Not-yet P/R |
|---|---|---|---|---|---|---|
| | baseline | | | | | |
