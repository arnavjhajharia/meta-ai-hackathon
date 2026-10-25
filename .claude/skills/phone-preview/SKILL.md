---
name: phone-preview
description: Check any web page we produce (the AB' tutorial player, a phone simulator, a judge dashboard) the way a person would see it on a phone. Use before calling any page done.
---

# Phone preview

1. Serve the page locally (for example `python -m http.server` from its folder).
2. With the Playwright MCP, open it at 390x844, once in light and once in dark colour scheme.
3. Exercise it like a person: tap a step, scrub the video, rotate to landscape (844x390).
4. Screenshot each state and open the screenshots with Read.
5. Check: text readable without zooming, nothing scrolls sideways, the current step is obvious,
   tap targets are at least 44px, captions do not cover the hands in the video, the teacher's
   name and tips read naturally. No em dashes anywhere in the copy.

Note: headless Chromium may not play H.264, so a black video frame in a screenshot is not a bug
on its own. Confirm playback separately with ffprobe or on a real phone.
