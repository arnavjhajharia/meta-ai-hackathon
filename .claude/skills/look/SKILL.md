---
name: look
description: Turn a run on a recorded clip into images and inspect them before reasoning about it. Use whenever detection results look wrong, an eval clip fails, or before changing any threshold.
---

# Look before you tune

Never explain a detection result from numbers alone. Make it visible first.

1. Run the clip through the pipeline and render two images (see CLAUDE.md Commands; if the
   renderer does not exist yet, build it first, it is worth it):
   - a **timeline**: for each tracked object, how much of the work area it covers over time,
     with the system's events as solid vertical lines and the human labels as dashed ones, and
     shaded spans where the work area was out of view;
   - a **frame grid**: about 12 evenly spaced frames with segmentation masks painted on and the
     current step and latest event written in the corner.
   Use the same colour for an object in both images.
2. Open both with Read.
3. Report, for each disagreement between system and labels: the time, the object whose line
   explains it, and what the frames show at that moment (hand over the bowl, glare, object
   outside the work area, work area not found, two objects confused).
4. Say whether the cause is segmentation, the measurement of the work area, or the step logic.
5. Propose the smallest change and name the other clips it could break.

This skill diagnoses. It does not change code.
