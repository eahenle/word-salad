# Experiment 2 partial-slate checkpoint

The Codex-agent slate reached the account usage cap after producing 311 valid
scheduled outcomes out of 320. This checkpoint is not a frozen experimental
dataset and has not been behaviorally or strategically scored. Scoring remains
deferred until the exact missing trials are rerun.

## Current state

- Valid scheduled outcomes: 311/320.
- Normal completed turns: 285.
- Protocol subject timeouts: 26. These are retained as outcomes and will not be
  retried.
- Infrastructure-invalid usage-cap rejections: 9 (`r0312` through `r0320`).
  Their attempt, completed record, raw trace, and stderr were archived under
  `invalidated-attempts/`; they were removed from active aggregates.
- Pending exact reruns: 9, enumerated with prompt hashes in
  `pending-quota-reruns.json`.
- Runtime-reported capacity return: August 19, 2026 at 7:10 AM America/Los_Angeles.

The partial integrity audit passes all stored prompt, trace, stderr, hash, and
generator invariants. No broken-pipe, runner-exception, or missing-final-message
failure occurred. The nine invalid attempts failed before a subject response
with the explicit runtime message that the usage limit had been reached.

## Tool-less regime

Official OpenAI documentation confirms that `gpt-5.6-sol` is exposed through
the Responses API and supports `reasoning.effort: xhigh`. This host has no
`OPENAI_API_KEY`, `OPENAI_ORG_ID`, or `OPENAI_PROJECT_ID` configured. Therefore
the exact tool-less regime is currently unavailable and no substitute model or
Codex-agent invocation will be mislabeled as tool-less.

## Resume command

After capacity returns, rerun exactly the pending IDs:

```bash
python3 -B experiment-2/run_codex.py \
  --root experiment-2 \
  --auth /Users/ahenle/MultiCliProfiles/codex/personal/auth.json \
  --isolation-validation experiment-2/results/isolation-validation.json \
  --trial-ids r0312 r0313 r0314 r0315 r0316 r0317 r0318 r0319 r0320 \
  --workers 4 --timeout 900
```

Then run the full integrity audit, score the completed slate, analyze observable
traces, perform the leakage audit, and freeze/tag Experiment 2.
