---
name: gpu-budget
description: Rules and steps for running segmentation on Modal within a $30 total budget. Use before any Modal deploy, run, or batch segmentation job.
---

# GPU budget ($30 on Modal, total, for the whole hackathon)

Prices (per second billing, nothing while idle): L4 about $0.80/h, A10 about $1.10/h,
A100 40GB about $2.10/h, H100 about $3.95/h. We use **L4** unless the human approves otherwise.

Before running:
1. Estimate frames x prompts x measured seconds per frame, and the dollar cost. Say it.
2. Check the segmentation cache first: only uncached frames should go to the GPU.
3. Batch frames per remote call (16 or so) for offline jobs.
4. Ask before `modal deploy` or `modal run`.

Server settings that must stay: no warm containers, a short idle window (about 90 s), at most
one GPU at a time.

After running:
1. `modal app list`: confirm nothing is still running; stop it if it is.
2. Report the actual GPU time and estimated spend.

Spending plan: about $5 segmenting real recordings, $5 experiments, $10 held back for
rehearsals and demo day. Stop and ask if a single job would exceed $2.
