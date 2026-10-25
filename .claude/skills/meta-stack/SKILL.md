---
name: meta-stack
description: Reference facts about the Meta services InStep targets (Muse Spark, SAM 3.1, Muse Voice Transcribe, the Ray-Ban Wearables Device Access Toolkit) and how to swap our stand-ins for them. Use when writing provider code, estimating cost, or on kickoff day.
---

# Meta stack reference (as of late Oct 2026; re-check against the official docs)

**Muse Spark** (Meta Model API, public preview, US developers at launch)
- OpenAI-compatible. Base URL `https://api.meta.ai/v1`, bearer `META_API_KEY`.
- Chat Completions and Responses endpoints. Inputs: text, image, video, PDF. No audio input.
- 1M-token context; structured outputs; function calling; prompt caching;
  `reasoning_effort` from minimal to xhigh. Reasoning tokens bill as output.
- Meta recommends a `developer` message over `system` for standing rules.
- Model ids seen: muse-spark-1.1, 1.2, 1.3. Use the newest the hackathon credits allow.
- Our use: one call over the whole teacher recording (send the video natively once available,
  keyframes with timestamps until then), and single-still judgements for "wait until" steps.

**SAM 3.1** (open weights under the SAM License; gated on Hugging Face as facebook/sam3.1,
SAM 3 as facebook/sam3)
- Text-prompted detection, segmentation and tracking in images and video. 3.1 adds Object
  Multiplex: much faster multi-object video tracking.
- Hosted on Meta Model API as `sam-3.1` since Sept 2026: up to 15,000 input frames per video and
  16 tracked objects per frame.
- Our stand-ins: SAM 3 on a Modal L4 GPU, or on the Mac via transformers (slow).

**Muse Voice Transcribe** (`muse-voice-transcribe-1.0`, API only, no open weights)
- Recordings: `POST https://api.meta.ai/v1/asr/transcribe`. Live: `wss://api.meta.ai/v1/asr/realtime`.
- Streaming, speaker diarization, endpointing and VAD built in. $3 per 1,000 audio minutes.
- Our stand-in: local Whisper.

**Ray-Ban glasses via the Wearables Device Access Toolkit** (developer preview, iOS and Android)
- Camera stream about 720p/30fps, in-stream and standalone photo capture, mics, speakers.
- Audio streaming and standalone high-quality capture are marked experimental.
- Mock Device Kit simulates a paired device, permissions and a media stream without hardware.

**Swapping a stand-in**: implement the provider behind the existing interface, run the eval with
the stand-in and with the Meta service, compare clip by clip, and only flip the default when the
human agrees the numbers are at least as good.
