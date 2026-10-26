"""Timeline of what the segmenter saw and what the system decided, for the look skill.

One row per tracked object (detection score inside the work area), one for hands and motion.
System events are solid vertical lines, human labels dashed, out-of-view spans shaded grey,
lesson step spans as coloured bands along the top.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from instep.learner.events import Event  # noqa: E402
from instep.learner.measure import FrameMeasure  # noqa: E402
from instep.lesson.schema import Lesson  # noqa: E402

EVENT_COLOURS = {
    "advance": "tab:green",
    "skip": "tab:red",
    "stall": "tab:orange",
    "frozen": "tab:gray",
    "resume": "tab:gray",
    "amount": "tab:purple",
    "not_yet": "tab:brown",
}


def object_colours(lesson: Lesson) -> dict[str, str]:
    cmap = plt.get_cmap("tab10")
    return {o.id: cmap(i % 10) for i, o in enumerate(lesson.objects)}


def render(
    lesson: Lesson,
    frames: list[FrameMeasure],
    events: list[Event],
    out: Path,
    labels: list | None = None,
    show_steps: bool = True,
    title: str = "",
) -> Path:
    ts = [m.t_s for m in frames]
    colours = object_colours(lesson)
    rows = [o for o in lesson.objects if o.id != lesson.work_area_object]
    n = len(rows) + 2
    fig, axes = plt.subplots(n, 1, figsize=(14, 0.9 * n + 1.6), sharex=True)
    axes = list(axes) if n > 1 else [axes]

    hidden, start = [], None
    for m in frames:
        if not m.work_area_visible and start is None:
            start = m.t_s
        elif m.work_area_visible and start is not None:
            hidden.append((start, m.t_s))
            start = None
    if start is not None and ts:
        hidden.append((start, ts[-1]))

    for ax, o in zip(axes, rows, strict=False):
        score = [
            (m.objects[o.id].score if o.id in m.objects and m.objects[o.id].in_work_area else 0)
            for m in frames
        ]
        ax.fill_between(ts, score, color=colours[o.id], alpha=0.6, step="mid")
        ax.set_ylim(0, 1)
        ax.set_ylabel(o.id, rotation=0, ha="right", fontsize=8)
        ax.set_yticks([])
    ax_wa = axes[len(rows)]
    ax_wa.fill_between(
        ts, [1 if m.work_area_visible else 0 for m in frames], color="black", alpha=0.25, step="mid"
    )
    ax_wa.fill_between(
        ts,
        [0.6 if m.hands_in_work_area else 0 for m in frames],
        color="tab:pink",
        alpha=0.7,
        step="mid",
    )
    ax_wa.set_ylabel("work area / hands", rotation=0, ha="right", fontsize=8)
    ax_wa.set_yticks([])
    ax_m = axes[-1]
    ax_m.plot(ts, [m.motion for m in frames], color="black", lw=0.8)
    ax_m.set_ylabel("motion", rotation=0, ha="right", fontsize=8)

    for ax in axes:
        for a, b in hidden:
            ax.axvspan(a, b, color="grey", alpha=0.2, lw=0)
        for e in events:
            ax.axvline(e.t_s, color=EVENT_COLOURS.get(e.kind, "black"), lw=1.4)
        for row in labels or []:
            ax.axvline(row.t_s, color=EVENT_COLOURS.get(row.kind, "black"), lw=1.4, ls="--")

    if show_steps:
        top = axes[0]
        for i, s in enumerate(lesson.steps):
            span = s.best_span
            if span:
                top.axvspan(
                    span.start_s,
                    span.end_s,
                    ymin=0.85,
                    ymax=1,
                    color=plt.get_cmap("Pastel1")(i % 9),
                )
                top.text(span.start_s, 1.02, s.id, fontsize=6, transform=top.get_xaxis_transform())
    for e in events:
        axes[0].text(
            e.t_s,
            1.25,
            f"{e.kind}:{e.step_id or ''}",
            fontsize=6,
            rotation=30,
            color=EVENT_COLOURS.get(e.kind, "black"),
            transform=axes[0].get_xaxis_transform(),
        )
    axes[-1].set_xlabel("seconds")
    fig.suptitle(title or lesson.title, fontsize=10, y=0.995)
    fig.tight_layout()
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=110)
    plt.close(fig)
    return out
