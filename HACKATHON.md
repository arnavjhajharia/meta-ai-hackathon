# The hackathon: everything we know

Read this before any decision about scope, the demo, or the submission. Facts marked
**(verify)** come from secondary sources or predate the Official Rules; the Official Rules,
published at kickoff, override everything here. Update this file when they disagree.

## The event

- **Name:** Meta Global AI Developer Hackathon 2026, run by Meta (Meta Superintelligence Labs)
  with Cerebral Valley. Virtual, worldwide, free for selected participants.
- **Build window:** Oct 26 to Nov 4, 2026 (10 days). Kickoff livestream Oct 26, workshops and
  office hours through Nov 4.
- **Submission deadline: Nov 4, 9:00 PM ET.** That is Nov 5, 7:30 AM IST for Arnav and
  Nov 4, 9:00 PM Eastern / 6:00 PM Pacific for the teammate in Canada.
- **Judging:** Nov 5 to 8. **Finals and winners:** Nov 9 (some sources say Nov 10 IST).
- Up to 20,000 accepted participants across both tracks.

## Our track: Indie Developer

- For individual builders and students. Despite "individual", the waiver allows **teams of up
  to 4**; one person submits and lists the others. **One track and one project per person.**
- Must be 18+. Meta and Cerebral Valley staff, sanctioned countries and listed excluded persons
  cannot enter. India and Canada are eligible.

### Prizes (Indie track, $400K total)

| Place | Prize |
|---|---|
| 1st | $150,000 |
| 2nd | $100,000 |
| 3rd | $75,000 |
| 4th | $50,000 |
| 5th | $25,000 |

Plus up to **$50K in bonus prizes** open to both tracks (for example community vote, most viral
project), separate from track prizes. The Startup track pays $550K ($250K for first).

The bonus prizes reward a demo video people want to share. Make it emotional and short.

## Themes (pick one, say it explicitly in the submission)

1. **Build for Your World:** solve a problem you know firsthand. **This is ours.** The story:
   know-how that lives only in a parent's or a technician's hands, and is lost with them.
   India (millions training for trades) and Canada (skilled-trades shortage) are our worlds.
2. Push the Frontier: robotics, science, manufacturing, energy, materials and other physical-world
   problems. A workshop or assembly demo would let us lean into this too, but we only claim one.

## Judging rubric (both tracks)

The landing page summary: "creativity, technical ambition, and whether it works."

| Criterion | Weight | What judges look for | How InStep earns it |
|---|---|---|---|
| **Impact** | 30% | Real-world potential, who benefits, fit with the theme | One sentence anyone gets: "Record once, anyone can learn it." Name real people who benefit (a learner far from home, an apprentice, the parent whose recipe would otherwise vanish). Show a real teacher, ideally a real parent. |
| **Use of Meta AI tooling** | 25% | Creative use that goes beyond a basic integration | Every model does work no other piece could: Muse Spark reads the *entire* teacher recording in one pass (1M context, native video); SAM 3.1 tracks hands and objects every frame; Muse Voice Transcribe captures the teacher's spoken tips and the learner's questions. The two-speed design (SAM every frame, Muse Spark only when judgement is needed) is a deliberate, explainable choice. Plus the Ray-Ban glasses as the capture and guidance device. |
| **Demo** | 25% | A working live demo plus the quality of the demo video | A 30-second moment that needs no explanation: the lesson waits, replays, then "Not yet. Maa waited until the seeds started to pop." Show all three modes, but lead with the strongest. Record the video early. |
| **Technical depth and execution** | 20% | Real difficulty, and that it actually works | Turning unscripted first-person footage into steps; calibrating the lesson by replaying the teacher as the first learner; only making claims the recording supports (amounts only glasses to glasses); and **numbers**: an eval on hand-labelled real attempts (step timing, skip and amount detection). Judges respect measured accuracy. |

Implication: Impact plus Demo is 55%. A beautiful, reliable demo of one mode beats three shaky
modes. Depth is only 20%, but it is where a judge decides whether we are serious.

## What we are given

- **$150 Meta Model API credits** per participant (verify: how they are activated, when they
  expire, whether teammates each get them). Meta Model API was US-only in public preview; check
  that it works from India and Canada with hackathon accounts.
- **Partner credits for some participants:** Baseten $100, Modal $100, Fireworks $25.
  (We currently have $30 on Modal.)
- **Models available:** Muse Spark series, Muse Wonder, Muse Image, Muse Glimmer, SAM 3.1, Meta
  open-weights models, and the Muse Code coding agent. Muse Voice Transcribe is on Meta Model API.
- Workshops and office hours through Nov 4: use them to ask about hosted SAM 3.1 limits, native
  video input to Muse Spark, and judging of glasses projects.
- (verify) One participant's notes say projects **must use the Meta Model API**. We do, through
  Muse Spark, SAM 3.1 and Muse Voice Transcribe. Do not let stand-ins (Claude, Whisper, SAM on
  Modal) remain in the final submitted build's main path unless the rules allow it.

## Submission (fill in from the Official Rules)

Expected, not yet confirmed:
- A working project built on the Meta stack.
- **A demo video**, probably 2 to 3 minutes; judges often stop watching after the limit, so the
  best moment goes in the first 30 seconds.
- A written description and the theme.
- Team member names and emails.
- Possibly a code repository link (keep the repo clean and the README runnable).

Open questions to answer from the Official Rules on day one:
1. Exact video length and format, and where it is hosted.
2. Is a public repository required? Any licence requirement?
3. Can we use existing code written before Oct 26 (our prototype)? If not, start clean.
4. Are non-Meta models allowed anywhere in the final build (Claude, Whisper)?
5. How is the "live demo" judged in finals: live call, recorded, or both?
6. Credit activation and limits.

## Our project, in the words we applied with

We're building InStep, which turns anyone's know-how into a lesson someone else can follow. So
much of what people know, like a mother's recipe, a technician's fix or a family craft, lives only
in their hands and is lost with them. InStep works three ways. A teacher can wear Meta Ray-Ban
glasses and simply do the task while talking it through, and InStep turns that unedited
first-person footage into a clean tutorial anyone can watch on their phone. A teacher can record on
a phone, as millions of people already do, and InStep turns it into a live lesson on the glasses
that watches your hands, waits while you work, replays the step you're stuck on, and warns you when
you skip one. Or, when teacher and learner both wear glasses, the learner is guided step by step
against the expert's own view, catching details a written recipe never could, like "she waited for
the seeds to pop before adding the leaves." Muse Spark reads each full recording in one pass to
understand the procedure, SAM 3.1 tracks the hands and objects that matter, and Muse Voice
Transcribe captures the teacher's tips and the learner's questions. Record once, any way you like,
and anyone can learn it.

Mode names used in the code: **AB** (glasses to glasses), **AB'** (glasses to phone),
**A'B** (phone to glasses). See CLAUDE.md.

## Schedule (internal deadlines are earlier than the real one on purpose)

| Date | Goal |
|---|---|
| Mon Oct 26 | Kickoff. Read the Official Rules, answer the open questions above, claim credits. Lesson schema agreed. |
| Tue Oct 27 | First real teacher recording on glasses. Teacher recording to Lesson working (stand-in models). |
| Wed Oct 28 | **AB' end to end on real footage**: a phone tutorial a stranger can follow. |
| Thu Oct 29 | Learner attempts recorded and labelled. AB offline on recordings, first eval numbers. |
| Fri Oct 30 | Swap stand-ins for Meta services (Muse Spark, hosted SAM 3.1, Muse Voice Transcribe). Re-run eval. |
| Sat Oct 31 | Live loop: glasses to phone app to backend and back, with spoken cues. |
| Sun Nov 1 | A'B if time allows. Otherwise harden AB. Rehearse the demo end to end. |
| **Mon Nov 2** | **Record the demo video.** Script first, shoot second. |
| Tue Nov 3 | Fix what the video exposed. Write the submission text. Freeze features. |
| Wed Nov 4 | Submit by noon ET, nine hours before the deadline. Nothing new after that. |

## Demo video outline (draft)

1. 0:00 to 0:10. A real teacher on glasses, mid-task, saying something no recipe would ("wait till
   it starts popping"). Title: Record once. Anyone can learn it.
2. 0:10 to 0:40. A learner on glasses: the lesson waits, replays a fumbled step, and catches a
   mistake in the teacher's own words. This is the moment.
3. 0:40 to 1:10. The same recording as a phone tutorial (AB'): dead time gone, tips intact.
4. 1:10 to 1:40. How it works, in one clean diagram: Muse Spark reads the whole recording, SAM 3.1
   watches the hands, Muse Voice Transcribe hears both people.
5. 1:40 to 2:10. The numbers from our eval, and who this is for.
6. Close on the teacher.

## Sources

- Official event page: https://dev.meta.ai/events/global-hackathon
- Cerebral Valley event overview and waiver (rubric, prizes, team size): via the application page
- Wearables Device Access Toolkit: https://developers.meta.com/wearables/faq/
- The Official Rules (link to be added at kickoff)
