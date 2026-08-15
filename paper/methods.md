# Methods skeleton

## Stimuli

Whitespace-delimited payload words were represented by source indices. Paired A
and B payloads used identical word multisets but different noncommuting operation
orders and distinct deterministic answer keys. Distractor streams were matched
per seed. Fixed, balanced-jitter, and uniform-random carrier masks altered signal
placement without changing aggregate lexical content.

## Subjects

Each Codex trial used a fresh ephemeral process or container, the exact declared
model and reasoning effort, and only the stimulus as user content. Hardened runs
used pinned Docker images with no repository mount or experiment files. Tool-less
runs disabled shell, filesystem, MCP, browser, application, and related features.
Complete emitted JSONL traces, stderr, exit status, timeout state, elapsed time,
thread identifier, and exposed usage metadata were preserved.

## Blinding and freezing

Prompt hashes, seed geometry, query order, scoring rules, and stopping rules were
frozen before inference. Responses froze before scoring. A failed attempt was
rerun only when the archived trace showed a pre-response transport/authentication
failure; timeouts after inference remained outcomes.

## Endpoints

The primary endpoint for equal-bag experiments was complete paired A/B
discrimination. Individual expected-answer recovery, counterpart answers,
all-shuffled target answers, malformed outputs, and timeouts were secondary.
Observable strategy scoring used emitted events only and did not infer private
chain of thought.

## Statistical reporting

Report scheduled-trial denominators, exact counts, rates, Wilson binomial
confidence intervals, paired discordances where prompts are matched, and control
target rates. Statistical tests summarize repeatability of one model/runtime and
are not population inference over models.

## Publication-closing task and stop rule

Experiment 6 first validated a five-symbol equal-bag state task on 20 fresh A
and 20 fresh B subjects. Each arm had to reach at least 18/20 exact normalized
outputs before controls. Version 1 failed at this stage (0/20 A, 0/20 B) and was
frozen. Version 2 passed (20/20 A, 20/20 B), after which ten independently
shuffled N=1 controls were run. The preregistered control gate required zero
exact A/B targets. Two controls emitted target A, so the gate failed. No noisy
carrier prompt was generated and experimental expansion stopped.
