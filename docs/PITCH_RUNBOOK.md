# LuminaX pitch runbook

## Session format

- Round 2 submission deadline: Saturday, 17 October 2026 at 11:59 PM IST.
- Proposed pitch date: Tuesday, 20 October 2026.
- Slot booking: organisers plan to share the booking link on Monday.
- Presentation: 10 minutes.
- Questions: 5 minutes.

Treat the Tuesday date as proposed until the organisers confirm it.

## Files to keep open

1. `output/pitch/LuminaX_Round2_Pitch_v5.pptx`
2. `docs/PITCH_SPEAKER_NOTES.md`
3. `docs/PITCH_QA.md`
4. `docs/PITCH_CLAIM_REGISTER.md`
5. `ROUND2_SUBMISSION.md`
6. `results/round2_summary.json`

Keep the repository page and the local evaluation studio ready as backup. Do
not depend on a live demo for the main presentation.

## Recommended speaker split

| Part | Speaker | Time |
|---|---|---:|
| Slides 1 to 6: problem, method, and worked example | Ahan | 4:55 |
| Slides 7 to 9: evidence and reliability | Enakshee | 3:05 |
| Slide 10: limits and close | Ahan | 1:20 |
| Buffer | Both | 0:40 |

If one person presents alone, keep the same slide timing.

## Before the call

- Confirm the final meeting link and slot.
- Join 15 minutes early from a laptop connected to power.
- Use headphones and test the microphone.
- Turn off notifications.
- Open the deck in presentation mode and confirm that charts render.
- Keep a PDF export ready only as a screen-sharing fallback.
- Keep the repository at the immutable `round2-final-v2` tag.
- Do not change the submitted algorithm during pitch preparation.
- Agree who answers algorithm, evaluation, and product questions.

## Presentation rules

- Finish slide 10 by 9 minutes 20 seconds.
- State that the results are public-simulator evidence, not a private-score
  guarantee.
- Say that the score is a matching priority, not a relationship probability.
- Explain the sparse-scenario failure before the judges ask.
- Do not claim fairness, production readiness, or real-world dating outcomes.
- Use slides 11 to 13 only during questions.

## Optional demo

The local evaluation studio can show public profiles, missing fields,
clarification choices, feasible pairs, daily selections, and matched-seed
results. Use it only if the judges ask to see an example.

Start it before the call:

```text
python frontend/build_dashboard_data.py
python -m http.server 8080 --directory frontend
```

Open `http://localhost:8080` and test one example before joining. If the page
does not load immediately, return to the deck. Do not troubleshoot during the
ten-minute talk.

## Recovery plan

| Problem | Response |
|---|---|
| Screen sharing fails | Send the deck or share the repository link in chat. |
| Slides fail to advance | Use the PDF fallback. |
| Demo fails | Continue with backup slide 11. |
| Audio drops | The teammate continues from the next slide. |
| A result is challenged | Open `docs/PITCH_CLAIM_REGISTER.md` and cite the source file. |
| A question needs more evidence | Say what is known, what is not known, and offer the exact reproducible check. |

## Final rehearsal

Run the full talk twice. The first rehearsal is for clarity. The second is
timed and should finish between 9:05 and 9:20. Then run a five-minute mock Q&A
using `docs/PITCH_QA.md`.
