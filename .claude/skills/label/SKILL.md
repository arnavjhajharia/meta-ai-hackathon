---
name: label
description: Help a human label a new learner recording against a lesson. Use when a new attempt arrives in data/recordings and has no labels yet.
argument-hint: "<recording.mp4> <lesson file>"
disable-model-invocation: true
---

# Labelling with a human in the loop

Arguments: $ARGUMENTS

1. Render a timestamped frame grid of the recording at two frames per second and open every page.
   Read the recorder's note for this file in notes.txt if there is one.
2. Draft labels: when each step was truly finished (the object visibly lands in the work area),
   and any skip, stall, clearly-wrong amount, or moving on before the teacher's "wait until".
3. Show the draft as a table with the frame time that justifies each row.
4. Stop. Ask the human to confirm or correct every row. Write the label file only after they
   confirm. Unconfirmed labels make every eval meaningless.
