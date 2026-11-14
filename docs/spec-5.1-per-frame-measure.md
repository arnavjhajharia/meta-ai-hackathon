# 5.1 — Per-frame measure for the live path

**Status:** draft for Ashmita ACK (PLAN phase 5.1).  
**Implements after ACK:** 5.2 (Arnav), 5.3 (device `FrameSource` + live backend).

## Goal

Offline replay today: `measure_clip()` runs the segmenter over the whole file once, caches by clip
hash, then `StepMachine.feed()` walks the list. Live glasses: frames arrive one at a time; there is
**no clip hash cache**. We need one stable per-frame API that `cli learn`, the simulator replay,
and the live websocket backend all use.

## Principles (from CLAUDE.md)

- Fast path only in the per-frame loop (segmenter → `FrameMeasure` → step machine).
- No reasoning model per frame.
- File replay keeps `measure_clip` disk cache unchanged (phase 1.4 decision).

## Types (existing)

| Type | Module | Role |
|---|---|---|
| `Frame` | `instep.sources.base` | `t_s`, RGB `image` from a `FrameSource` |
| `FrameMeasure` | `instep.learner.measure` | One frame of reduced evidence |
| `Measurer` | `instep.learner.measure` | Holds segmenter + motion state (`_prev`) |
| `ClipMeasures` | `instep.learner.measure` | Batch output + cache envelope |

## Public API (proposed)

### `Measurer.measure` (already exists)

```python
def measure(self, t_s: float, image: np.ndarray) -> FrameMeasure: ...
```

Single entry point for live and batch. **Session rule:** one `Measurer` instance per learner
session; never share across lessons or parallel sessions without reset.

### `measure_clip` (unchanged)

Batch helper: iterate `(t_s, image)`, call `measurer.measure`, write `ClipMeasures` to cache.
Signature stays as today.

### `measure_stream` (new thin wrapper, 5.2)

```python
def measure_stream(
    lesson: Lesson,
    segmenter: Segmenter,
    frames: Iterator[tuple[float, np.ndarray]],
    *,
    min_score: float = 0.30,
) -> Iterator[FrameMeasure]:
    """No disk cache. For live sources and tests."""
```

Implementation: construct one `Measurer`, yield `measure(t, img)` for each frame. No new types.

### Optional: `LearnerSession` (5.2, convenience)

```python
@dataclass
class LearnerSession:
    lesson: Lesson
    measurer: Measurer
    machine: StepMachine

    def tick(self, frame: Frame) -> list[Event]:
        return self.machine.feed(self.measurer.measure(frame.t_s, frame.image))
```

Not required for 5.1 ACK; documents how Ashmita's backend composes pieces.

## Caching

| Path | Cache |
|---|---|
| `measure_clip` + `FileReplay` | Yes — key = SHA-256 of file + prompts + segmenter + fps + width + `v=3` |
| `measure_stream` / live `FrameSource` | **No** disk cache |
| Live segmenter | May add an in-memory LRU keyed by frame content hash later; out of scope for 5.1 |

## Sampling and image size

| Setting | Source | Live default |
|---|---|---|
| Sample rate | `Config.learner_fps` | Same as file replay (e.g. 2 fps) |
| Segment width | `SEG_WIDTH` (640 in cli/sim) | Same; device may downscale before send |
| Judge still | `FrameSource.still(t_s)` | Higher width (768 today); not per-frame measure |

Device `FrameSource` is responsible for emitting frames at `learner_fps` (drop or bucket on the
phone). Backend must not assume every camera frame arrives.

## Live backend contract (websocket extension)

Current sim: client sends `{"type":"tick","t":…}` against **precomputed** measures.

Live mode (new message types, same `/ws`):

### Client → server

```json
{
  "type": "frame",
  "t_s": 12.5,
  "image_jpeg_b64": "..."
}
```

Or binary multipart later; v1 matches phone upload constraints (base64 JPEG).

### Server → client

```json
{
  "type": "frame_result",
  "t_s": 12.5,
  "measure": { "visible": true, "hands": false, "seen": ["pan", "mustard_seeds"] },
  "events": [ { "t_s": 12.5, "kind": "advance", "step_id": "...", ... } ]
}
```

`measure` in the wire payload is a **summary** (same fields sim already sends on replay ticks),
not the full `FrameMeasure`, to save bandwidth. Full structure stays in Python.

### Session open (live)

```json
{ "type": "open_live", "lesson": "<id>", "judge": true }
```

Server creates `LearnerSession` with `still_at` / `reference_for` from the device source or
stubs. No `measure_clip` call.

Replay mode keeps `open` + `tick` behaviour unchanged.

## Threading and latency

- Segmenter runs in a worker thread pool (`asyncio.to_thread` pattern from sim `Session` open).
- Target: frame received → last event in `events` **&lt; ~1 s** on the fast path (PLAN phase 5).
- 5.2 owns benchmarks; 5.1 only requires **one measure call per sampled frame**, no batch lookahead.

## Failure behaviour

| Condition | Behaviour |
|---|---|
| Segmenter error on one frame | Log, emit no events for that frame; do not reset `Measurer` motion state |
| Work area not visible | `FrameMeasure.work_area_visible == false`; machine may `frozen` |
| Session reset | New `Measurer` + `StepMachine.reset()`; live seek-back is N/A |

## Testing (5.2)

- `measure_stream` on synthetic frames matches last N frames of `measure_clip` on the same file.
- Fake segmenter tests: no GPU, no cache dir required for stream path.

## Open decisions (owner)

1. **Wire format:** JPEG base64 in JSON vs binary websocket frame (proposal: JSON v1 for Mock Kit).
2. **Back-pressure:** drop frames if segmenter falls behind vs queue (proposal: drop to latest to
   keep latency bounded).
3. **`LearnerSession` type:** module-level dataclass vs inline in `sim/server.py` (proposal:
   `instep.learner.session` when 5.2 lands).

---

**ACK checklist (Ashmita):**

- [ ] One `Measurer.measure` call per live frame; `measure_clip` cache unchanged
- [ ] `frame` / `frame_result` websocket shapes (or binary alternative)
- [ ] Sampling: phone buckets to `learner_fps`
- [ ] Back-pressure policy (open decision 2)