---
name: eval
description: Improve learner-side detection against the hand-labelled clips without regressions. Use for any change to detection logic, thresholds, calibration or segmentation prompts.
argument-hint: "[focus, e.g. skip detection, latency, amounts]"
---

# Eval loop

Focus: $ARGUMENTS

1. Run the full eval and save the table as the "before".
2. For each failing clip, use the `look` skill. For any clip where the cause is not obvious,
   ask the `frame-critic` subagent for an independent view.
3. Change one thing at a time. Re-run the eval after each change. Revert anything that breaks a
   clip that passed in the baseline.
4. Never create, edit or delete labels, and never change the scoring code, to make a clip pass.
   If a label looks wrong, list it for the human.
5. Never tune thresholds on synthetic clips; they are far cleaner than real footage.

Finish with: before table, after table, each change in one sentence with the image evidence
behind it, suspected label errors, and any spend on paid models or GPUs.
