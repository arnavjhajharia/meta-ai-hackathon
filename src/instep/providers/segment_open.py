"""Open, ungated segmenters on the Mac (stand-ins until SAM 3 / hosted SAM 3.1).

``GdinoSam2``: Grounding DINO finds boxes for text prompts, SAM 2.1 turns boxes into masks.
``Sam3Local``: SAM 3 (gated on Hugging Face) does both from text, once access is granted.
Both return the same ``Detection`` list, so callers never know which one ran.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from instep.providers.base import Detection


def _device():
    import torch

    return "mps" if torch.backends.mps.is_available() else "cpu"


def _phrase(prompt: str) -> str:
    return prompt.lower().strip().rstrip(".")


@dataclass
class GdinoSam2:
    detector_id: str = "IDEA-Research/grounding-dino-base"
    sam_id: str = "facebook/sam2.1-hiera-small"
    box_threshold: float = 0.30
    text_threshold: float = 0.25
    max_per_prompt: int = 4
    with_masks: bool = True
    name: str = "gdino-sam2"
    _models: dict = field(default_factory=dict, repr=False)

    def _load(self) -> None:
        if self._models:
            return
        from transformers import (
            AutoModelForZeroShotObjectDetection,
            AutoProcessor,
            Sam2Model,
            Sam2Processor,
        )

        from instep.config import model_path

        dev = _device()
        det, sam = model_path(self.detector_id), model_path(self.sam_id)
        self._models["dproc"] = AutoProcessor.from_pretrained(det)
        self._models["det"] = (
            AutoModelForZeroShotObjectDetection.from_pretrained(det).to(dev).eval()
        )
        if self.with_masks:
            self._models["sproc"] = Sam2Processor.from_pretrained(sam)
            self._models["sam"] = Sam2Model.from_pretrained(sam).to(dev).eval()
        self._models["dev"] = dev

    def segment(
        self, image: np.ndarray, prompts: list[str], solo: list[str] | None = None
    ) -> list[Detection]:
        """``solo`` prompts get their own detector pass: with many phrases in one pass Grounding
        DINO often gives a box the wrong phrase, and the work area must not be mislabelled."""
        from PIL import Image

        if not prompts:
            return []
        self._load()
        pil = Image.fromarray(image)
        solo = [p for p in (solo or []) if p in prompts]
        found: list[Detection] = []
        for p in solo:
            found += self._detect(pil, [p])
        rest = [p for p in prompts if p not in solo]
        if rest:
            claimed = [d.box for d in found]
            found += [
                d for d in self._detect(pil, rest) if all(_iou(d.box, c) < 0.7 for c in claimed)
            ]
        return self._masks(pil, found)

    def _detect(self, pil, prompts: list[str]) -> list[Detection]:
        import torch

        m = self._models
        phrases = [_phrase(p) for p in prompts]
        inputs = m["dproc"](images=pil, text=[phrases], return_tensors="pt").to(m["dev"])
        with torch.no_grad():
            out = m["det"](**inputs)
        res = m["dproc"].post_process_grounded_object_detection(
            out,
            inputs.input_ids,
            threshold=self.box_threshold,
            text_threshold=self.text_threshold,
            target_sizes=[pil.size[::-1]],
        )[0]
        labels = res.get("text_labels", res.get("labels"))
        found: list[Detection] = []
        for box, score, label in zip(
            res["boxes"].tolist(), res["scores"].tolist(), labels, strict=False
        ):
            prompt = _match_prompt(str(label), prompts, phrases)
            if prompt is None:
                continue
            found.append(Detection(prompt=prompt, score=float(score), box=tuple(box), mask=None))
        return _top_per_prompt(found, self.max_per_prompt)

    def _masks(self, pil, found: list[Detection]) -> list[Detection]:
        import torch

        m = self._models
        if self.with_masks and found:
            boxes = [[list(d.box) for d in found]]
            sin = m["sproc"](images=pil, input_boxes=boxes, return_tensors="pt").to(m["dev"])
            with torch.no_grad():
                sout = m["sam"](**sin, multimask_output=False)
            masks = m["sproc"].post_process_masks(sout.pred_masks.cpu(), sin["original_sizes"])[0]
            for d, mk in zip(found, masks, strict=False):
                d.mask = mk[0].numpy().astype(bool)
        return found


def _match_prompt(label: str, prompts: list[str], phrases: list[str]) -> str | None:
    """Grounding DINO returns the matched words, which may be a fragment of a phrase."""
    label = label.strip().lower()
    if not label:
        return None
    for prompt, phrase in zip(prompts, phrases, strict=False):
        if label == phrase:
            return prompt
    best, best_overlap = None, 0
    words = set(label.split())
    for prompt, phrase in zip(prompts, phrases, strict=False):
        overlap = len(words & set(phrase.split()))
        if overlap > best_overlap:
            best, best_overlap = prompt, overlap
    return best


def _top_per_prompt(found: list[Detection], k: int) -> list[Detection]:
    out: list[Detection] = []
    for prompt in dict.fromkeys(d.prompt for d in found):
        mine = sorted((d for d in found if d.prompt == prompt), key=lambda d: -d.score)
        kept: list[Detection] = []
        for d in mine:
            if all(_iou(d.box, e.box) < 0.6 for e in kept):
                kept.append(d)
            if len(kept) == k:
                break
        out += kept
    return out


def _iou(a: tuple, b: tuple) -> float:
    x0, y0 = max(a[0], b[0]), max(a[1], b[1])
    x1, y1 = min(a[2], b[2]), min(a[3], b[3])
    inter = max(0.0, x1 - x0) * max(0.0, y1 - y0)
    union = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter
    return inter / union if union > 0 else 0.0


@dataclass
class Sam3Local:
    model_id: str = "facebook/sam3"
    threshold: float = 0.5
    name: str = "sam3"
    _models: dict = field(default_factory=dict, repr=False)

    def segment(
        self, image: np.ndarray, prompts: list[str], solo: list[str] | None = None
    ) -> list[Detection]:
        """SAM 3 grounds one concept per pass already, so ``solo`` changes nothing."""
        import torch
        from PIL import Image
        from transformers import Sam3Model, Sam3Processor

        if not self._models:
            dev = _device()
            self._models["proc"] = Sam3Processor.from_pretrained(self.model_id)
            self._models["model"] = Sam3Model.from_pretrained(self.model_id).to(dev).eval()
            self._models["dev"] = dev
        m = self._models
        pil = Image.fromarray(image)
        found = []
        for prompt in prompts:
            inputs = m["proc"](images=pil, text=_phrase(prompt), return_tensors="pt").to(m["dev"])
            with torch.no_grad():
                out = m["model"](**inputs)
            r = m["proc"].post_process_instance_segmentation(
                out,
                threshold=self.threshold,
                mask_threshold=0.5,
                target_sizes=inputs.get("original_sizes").tolist(),
            )[0]
            for mask, box, score in zip(
                r["masks"], r["boxes"].tolist(), r["scores"].tolist(), strict=False
            ):
                found.append(
                    Detection(
                        prompt=prompt,
                        score=float(score),
                        box=tuple(box),
                        mask=mask.cpu().numpy().astype(bool),
                    )
                )
        return found
