# 6.1 — Voice Q&A answer API

**Status:** draft for Ashmita ACK (PLAN phase 6.1).  
**Implements after ACK:** 6.2 (Arnav answer provider), 6.3 (Ashmita voice pipeline).

## Goal

During a live lesson, the learner asks a short question ("How much salt?", "Is it done yet?").
Local Whisper turns speech into text. A single **answer** call returns text for TTS on the glasses
(open-ear). The answer uses the **Lesson** (tips, amounts, step instructions) and one **learner
still**, in the teacher's voice. Optional: suggest replaying a teacher clip for that step.

Not in scope: streaming LLM, per-frame calls, or changing step state.

## Placement in the stack

| Role | Provider interface | Model (default) |
|---|---|---|
| Transcribe question | `Transcriber` (existing) | Whisper local |
| Answer | **`Answerer`** (new) | Claude Sonnet via Anthropic API |
| Speak | Ashmita pipeline | Phone TTS → glasses audio |

Same rule as judge and understander: one interface, config-swappable implementation, fake for
tests, cache on exact inputs.

## `Answerer` protocol (proposed)

Module: `instep.providers.base` (alongside `StillJudge`).

```python
class AnswerRequest(BaseModel):
    question: str  # normalised transcript, one utterance
    lesson_id: str
    step_id: str | None  # current step from StepMachine; None if before start or after finish
    step_index: int | None
    language: str | None  # ISO 639-1 hint from Lesson or transcript


class AnswerResponse(BaseModel):
    text: str  # short, spoken, teacher voice; no markdown
    cite_step_id: str | None = None  # step the answer mainly draws from
    suggest_replay: bool = False  # if true, client may play teacher span for cite_step_id
    confidence: float = Field(ge=0, le=1, default=0.8)


class Answerer(Protocol):
    name: str

    def answer(
        self,
        req: AnswerRequest,
        lesson: Lesson,
        learner_jpeg: bytes,
        *,
        history: list[tuple[str, str]] | None = None,  # optional (q, a) pairs this session
    ) -> AnswerResponse: ...
```

### Inputs

| Input | Required | Notes |
|---|---|---|
| `question` | yes | From transcriber; trim, max ~500 chars |
| `lesson` | yes | Full `Lesson` pydantic model (tips, amounts, wait copy) |
| `learner_jpeg` | yes | Current work-area still from `FrameSource.still(now)` or last good frame |
| `step_id` / `step_index` | no | Lets the model focus; omit when unknown |
| `history` | no | Last 2 Q&A turns max for follow-ups ("And the cumin?") |

### Output

- **`text`:** 1–3 sentences, plain language, warm. Use Lesson quotes when available (`Tip.quote`,
  `cue_not_yet`, amount cues). No em dashes (project copy rule).
- **`suggest_replay`:** `true` when seeing the teacher do it beats words (e.g. "show me the
  spoonful again"). Client uses `lesson` spans / AB' chapter times when present.
- **`confidence`:** for logging and fallback ("I'm not sure from here. Look at the pan.").

### What the model sees

One multimodal message (images + text), same family as judge:

1. Learner JPEG (current view).
2. Text block:
   - Lesson title, task, language.
   - Current step title + instruction (if `step_id` set).
   - Compact list: all step titles; tips on current and adjacent steps; `Amount` and `WaitUntil`
     text for current step.
   - The question.
   - System rules: answer only from Lesson + visible work; if view is unclear, say so; stay short.

No video, no frame grid (principle 3). Reference teacher still is **optional** future enhancement
if answers hallucinate; not required for 6.1 ACK.

## Caching and spend

```python
cache.key(
    provider="answer",
    lesson_id=lesson.id,
    lesson_rev=hash_of_lesson_json_or_updated_at,
    question=normalised_question,
    step_id=req.step_id,
    image_sha256=sha256(learner_jpeg),
    model=...,
    prompt_version="answer_v1",
)
```

- Cache namespace: `"answer"` (alongside `"judge"`, `"draft"`).
- Respect `INSTEP_SPEND_CAP_USD`.
- Rate limit: at most one in-flight answer per session; ignore overlap while busy (Ashmita UX).

Config: `INSTEP_ANSWER_MODEL` (default same family as judge, e.g. Sonnet), `answer: str = "claude"`
in `Config`.

## HTTP / websocket surface (Ashmita, 6.3)

Lives on the live backend (extends phase 5 server), not on the offline simulator.

### Client → server

```json
{
  "type": "question",
  "text": "how much mustard seed",
  "t_s": 18.2
}
```

Server resolves still at `t_s`, current `step_id` from open `LearnerSession`, calls `answer()`.

### Server → client

```json
{
  "type": "answer",
  "text": "Just a spoonful, like Maa showed. Not more.",
  "suggest_replay": false,
  "cite_step_id": "add_mustard"
}
```

Client runs TTS on `text`. If `suggest_replay`, play teacher media for `cite_step_id` when wired.

## Fake provider (tests, 6.2)

```python
class FakeAnswerer:
    name = "fake-answer"

    def answer(self, req, lesson, learner_jpeg, *, history=None) -> AnswerResponse:
        return AnswerResponse(text="Stub.", cite_step_id=req.step_id)
```

Contract tests: question mentioning "mustard" on chai/tadka fixture Lesson returns text containing
a known tip string when using a scripted fake.

## Safety and scope

- Refuse off-task questions politely ("Let's stay on the chai for now.").
- No tool use, no Lesson mutation.
- Amount questions: cite `Amount` and calibrated `teacher_value` in words, not raw fractions,
  unless the teacher did ("about two spoons").

## Open decisions (owner)

1. **Reference teacher still in prompt?** Proposal: 6.2 launch without; add if eval shows drift.
2. **Hindi questions:** answer in the language of the question or always Lesson `language`
   (proposal: match question if Whisper reports it).
3. **`history` length:** 0 vs 2 turns (proposal: 2).

---

**ACK checklist (Ashmita):**

- [ ] `Answerer` / `AnswerRequest` / `AnswerResponse` fields
- [ ] `question` / `answer` websocket messages on live backend
- [ ] TTS + `suggest_replay` behaviour
- [ ] Language policy (open decision 2)