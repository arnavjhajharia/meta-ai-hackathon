---
name: lesson-review
description: Review a Lesson produced from a teacher recording before anything else uses it. Use whenever a lesson file is created or changed, or when a learner-side result looks wrong and the lesson might be the cause.
---

# Lesson review

A wrong lesson poisons every mode (AB, AB', A'B), so check it against the recording itself,
not against what the model claimed.

1. Render a timestamped frame grid of the teacher recording (about one frame per second) and
   open every page with Read. Read the transcript too if there is one.
2. For each step, cite the frame times that show it starting and finishing. Flag any step whose
   times are off by more than about two seconds, and any real step the lesson missed.
3. Check every object prompt: is it a short, concrete, visually distinctive noun phrase that a
   segmenter could find on its own ("sev", "chopped onion")? Flag vague ones ("toppings",
   "ingredients") and pairs that look alike on camera.
4. Check every tip: did the teacher actually say or do this? Quote the transcript line or cite the
   frame. Tips must be in the teacher's words where possible. Remove anything invented.
5. Check every "wait until" condition: could a person judge it from a single still photo? If not
   ("it smells nutty"), say so; it cannot be checked by the camera.
6. Check the lesson records how it was made (teacher on glasses or on a phone).

Report a table: step, verdict (ok / fix), evidence, suggested fix. Do not edit the lesson
yourself unless asked; the human decides.
