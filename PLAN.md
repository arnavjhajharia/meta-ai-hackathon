# InStep plan

The full vision, in phases. Each phase has an owner, what "done" means, and how we check it.
Read `CLAUDE.md` for vocabulary (A, A', B, B', AB, AB', A'B) and design principles, and
`HACKATHON.md` for the event, rubric and demo outline.

Owners: **Arnav** (no glasses, works from recorded footage) and **Ashmita** (in Canada:
has the Ray-Bans, builds the phone app, records teacher sessions and learner attempts).

## Where we are (Nov 12)

All work so far is from kickoff day (Oct 26). The Nov 4 submission deadline has passed.

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
- Nothing for A, AB', the Meta services, the live loop, voice, the README or the demo video.

## How the phases fit

```
0 Reset ──> 1 Close day 1 ──> 2 AB checks ──┐
                    │                       ├──> 6 Live loop ──> 7 Voice ──> 8 Demo
                    └──> 3 A pipeline ──> 4 AB'
5 Meta swap (any time once credits work; rerun every eval after)
Recording (Ashmita) runs alongside everything from phase 1 on.
```

Rubric reminder: Impact and Demo are 55%. One mode that works every time beats three shaky ones.
If time runs short, ship phases 1, 2 and 8 with AB as the lead, and cut 4 or 7 before cutting
the eval.

---

## Phase 0: Reset (both, short)

- [ ] Make a fresh `.venv`, `pip install -e '.[dev]'`, tests and lint green.
- [ ] Decide what we are aiming for now (the finals, a later hackathon, a portfolio piece) and
      update `HACKATHON.md` with whatever the Official Rules said, especially whether non-Meta
      models may stay in the main path.
- [ ] Check Meta Model API access from India and Canada, and the credit balance.
- [ ] Update "Current focus" in `CLAUDE.md` to point at this file.

**Done when:** `pytest -q` and lint pass on a clean checkout, and we have written answers to the
rules and credits questions.

## Phase 1: Close day 1, A'B and B on recorded footage (Arnav)

Pick **one task** for everything (masala chai fits the story; the paper boat is easier to see).
Use the same task for the tutorial, the hand-written Lesson and the learner attempts.

- [ ] Generate the A'B Lesson from the chosen tutorial, run `/lesson-review`, commit it to
      `data/lessons/generated/`.
- [ ] Hand-write the AB Lesson (`authored: hand_written`) with at least one amount and one
      "wait until" step, run `/lesson-review`, commit it to `data/lessons/hand/`.
- [ ] Label at least two learner clips with `/label` (a human confirms every row), commit them
      to `data/labels/`.
- [ ] Run `/eval` against both Lessons and record baseline numbers in `runs/` and in this file.
- [ ] `finish()`: emit a final event when the recording ends partway through (unfinished step).
- [ ] Wire `FrameSource` into `sim/server.py` and `cli learn` (a file source now; a device
      source later), so no code reads video files directly except the file source.

**Ashmita, in parallel:** record two or three learner attempts of the chosen task (chest phone
stand-in is fine, mark it in the filename), at least one with a deliberate skip and one stall.

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
- [ ] Label the amount and not-yet moments on the clips; run `/eval` before and after.

**Done when:** on at least one labelled AB clip, `amount` and `not_yet` fire at the right moments
with no regressions on phase 1 numbers.

## Phase 3: A pipeline, glasses teacher to Lesson (Ashmita records, Arnav builds)

Replaces the hand-written AB Lessons with real ones.

- [ ] **Ashmita:** record two or three real teacher sessions on the glasses, talking it through.
      Ideally a real parent for the demo task.
- [ ] Understander takes the **whole** recording in one pass (Muse Spark has 1M context and
      native video; Claude on keyframes plus transcript until then). Output is the same
      DraftLesson the A' path makes, plus amounts and "wait until" moments.
- [ ] Provenance `teacher_device: glasses`, so `claims()` includes amount and wait_until.
- [ ] Calibrate by replaying the teacher's own recording through the learner machinery (phase 2
      fills in the amounts and reference stills).
- [ ] `/lesson-review` on each generated Lesson; diff against the hand-written one for the same
      task.

**Done when:** a learner clip scores at least as well against the generated AB Lesson as against
the hand-written one.

## Phase 4: AB', glasses recording to a watchable tutorial (Arnav)

- [ ] Cut dead time: keep each step's calibrated span plus padding; drop spans with no hands in
      the work area and no speech.
- [ ] Chapters from the steps, tips as captions in the teacher's words, amounts shown on screen.
- [ ] Render with ffmpeg (no new dependency) to an mp4 plus a chapter JSON.
- [ ] A phone player page (chapters, captions, replay step). Run `/phone-preview` at 390x844.
- [ ] Check: someone who has not seen the raw footage follows the tutorial and completes the task.

**Done when:** a 10 to 20 minute raw recording becomes a 2 to 4 minute tutorial, and one stranger
gets through it.

## Phase 5: Swap stand-ins for Meta services (Arnav, once credits work)

Config changes only. Nothing outside `providers/` should change.

- [ ] `docs-scout` for current API shapes; `/meta-stack` for cost.
- [ ] Muse Spark as understander and still judge (OpenAI-compatible, api.meta.ai/v1).
- [ ] Hosted SAM 3.1 as segmenter.
- [ ] Muse Voice Transcribe as transcriber.
- [ ] Register each in `providers/registry.py`, keep fakes for tests, keep the cache in front.
- [ ] Rerun every eval and every Lesson; record before and after numbers in this file.

**Done when:** the main path runs with zero Anthropic, Whisper or Modal calls, and eval numbers
are no worse (or the drop is explained).

## Phase 6: Live loop on the glasses (Ashmita builds the app, Arnav builds the backend)

- [ ] Device `FrameSource`: Mock Device Kit first, then the real Wearables Device Access Toolkit
      720p stream, both through the same interface the simulator uses.
- [ ] Phone app sends frames (sampled) to the backend; backend runs measure plus `StepMachine`
      and sends events back.
- [ ] Spoken cues through the glasses' open-ear speakers (phone TTS to start).
- [ ] Latency budget: frame to cue under about 1 s on the fast path. Measure it, show it.
- [ ] Segmenter placement: hosted SAM 3.1 vs a GPU box; check `/gpu-budget` before any Modal use.

**Done when:** a learner wearing the glasses completes the demo task live, hearing cues, with the
lesson waiting, replaying and catching a skip.

## Phase 7: Voice questions (both, if time)

- [ ] Learner asks a question ("how much salt?"); transcribe with Muse Voice Transcribe.
- [ ] Answer from the Lesson (tips, amounts) plus the current still, in the teacher's voice.
- [ ] Answer replays the teacher's clip for that step when that helps more than words.

**Done when:** three scripted questions get correct, short answers during a live run.

## Phase 8: Demo and submission (both)

- [ ] Script the video from the outline in `HACKATHON.md` (best moment in the first 30 s).
- [ ] Record with a real teacher and a real learner, lead with AB.
- [ ] Eval numbers on screen (step timing, skip, amount, not-yet).
- [ ] README: what it is, how to run the simulator on a recorded clip, the architecture diagram.
- [ ] Clean repo: no secrets, no videos, runnable from a fresh clone.
- [ ] Rehearse the live demo end to end twice, with a recorded fallback ready.

**Done when:** the video is uploaded, the README runs on a fresh clone, and the live demo has
gone right twice in a row.

---

## Risks

| Risk | What we do |
|---|---|
| Glasses footage is slow to get | Chest-phone stand-ins for phases 1 and 2; hand-written AB Lessons until phase 3. |
| Meta credits or API access do not work from India or Canada | Stand-ins stay behind the same interfaces; ask in office hours early. |
| SAM too slow for live use | Lower the sampling rate; hosted SAM 3.1; fall back to the recorded demo with the simulator. |
| Thresholds tuned on too few clips | At least two labelled clips per behaviour; never tune on synthetic footage. |
| Modal budget ($30) | `/gpu-budget` before any run; never keep a container warm; check `modal app list` after. |

## Eval log

Record numbers here after every `/eval` run that changes detection.

| Date | Change | Clips | Advance timing (median s) | Skip P/R | Amount P/R | Not-yet P/R |
|---|---|---|---|---|---|---|
| | baseline | | | | | |
