# Cost-truncated tool-less pilot analysis

## Result

The no-tool model recovered the expected ordered answer in **35/40 N=2 signal
trials (87.5%)**, including both A and B answers in **16/20 equal-word-bag
pairs (80.0%)**. The same 40 prompts produced 29/40 expected answers and
11/20 discriminating pairs under the Codex-agent regime. All 40 clean trials
succeeded in both regimes.

This is direct behavioral evidence that shell, filesystem access, and an agentic
tool loop are not required for ordered-lane recovery at N=2. It strengthens—but
does not prove—the transformer-level source-separation interpretation: the two
regimes also differ in system context and runtime, private reasoning was not
exposed, and this was not a randomized sample of models.

The tool-less control cohort stopped at 14/20 prompts for cost. Five returned a
response and nine reached the approximately 600-second connection limit. None of
the 14 produced target answer A or B; the matched Codex controls also produced no
target answer. Because most tool-less controls are nonresponses, this is weak
evidence about completed-response answer bias but strong evidence of an effort
explosion when no intact lane exists.

## Answer identity and success

| regime | condition | N | stimulus | scheduled | completed | timeouts | A | B | other/no answer | exact | expected | scheduled rate [95% CI] | completed-only | final-text discovery |
| --- | --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: | ---: |
| codex_agent | clean | 1 | A | 20 | 20 | 0 | 20 | 0 | 0 | 8 | 20 | 100.0% [83.9%, 100.0%] | 100.0% | 0 |
| tool_less | clean | 1 | A | 20 | 20 | 0 | 20 | 0 | 0 | 20 | 20 | 100.0% [83.9%, 100.0%] | 100.0% | 0 |
| codex_agent | clean | 1 | B | 20 | 20 | 0 | 0 | 20 | 0 | 8 | 20 | 100.0% [83.9%, 100.0%] | 100.0% | 0 |
| tool_less | clean | 1 | B | 20 | 20 | 0 | 0 | 20 | 0 | 20 | 20 | 100.0% [83.9%, 100.0%] | 100.0% | 0 |
| codex_agent | signal | 2 | A | 20 | 20 | 0 | 15 | 0 | 5 | 11 | 15 | 75.0% [53.1%, 88.8%] | 75.0% | 0 |
| tool_less | signal | 2 | A | 20 | 20 | 0 | 17 | 0 | 3 | 10 | 17 | 85.0% [64.0%, 94.8%] | 85.0% | 0 |
| codex_agent | signal | 2 | B | 20 | 20 | 0 | 1 | 14 | 5 | 6 | 14 | 70.0% [48.1%, 85.5%] | 70.0% | 0 |
| tool_less | signal | 2 | B | 20 | 20 | 0 | 0 | 18 | 2 | 12 | 18 | 90.0% [69.9%, 97.2%] | 90.0% | 0 |
| codex_agent | all_shuffled | 2 | none | 14 | 11 | 3 | 0 | 0 | 14 | 0 | 0 | 0.0% [0.0%, 21.5%] | 0.0% | 11 |
| tool_less | all_shuffled | 2 | none | 14 | 5 | 9 | 0 | 0 | 14 | 0 | 0 | 0.0% [0.0%, 21.5%] | 0.0% | 2 |

For all-shuffled rows, `expected` is structurally zero because there is no
designated answer key; columns A and B are the relevant target-answer endpoint.

## Paired A/B discrimination at N=2

A pair counts only when its A stimulus produced answer A and its B stimulus
produced answer B. The aggregate whitespace-delimited word bag is identical
within every A/B pair.

| regime | pairs | both expected | rate [95% CI] | A-only | B-only | neither | same-A error | same-B error |
| --- | ---: | ---: | --- | ---: | ---: | ---: | ---: | ---: |
| tool_less | 20 | 16 | 80.0% [58.4%, 91.9%] | 1 | 2 | 1 | 0 | 0 |
| codex_agent | 20 | 11 | 55.0% [34.2%, 74.2%] | 4 | 3 | 2 | 0 | 0 |

## Matched regime comparison

| endpoint cohort | matched | both | tool-less only | Codex only | neither |
| --- | ---: | ---: | ---: | ---: | ---: |
| clean — expected_answer_success | 40 | 40 | 0 | 0 | 0 |
| signal — expected_answer_success | 40 | 27 | 8 | 2 | 3 |
| all_shuffled — produced_A_or_B_target_answer | 14 | 0 | 0 | 0 | 14 |
| signal_paired_A_B — both_ordered_answers_expected | 20 | 10 | 6 | 1 | 3 |

At the individual-signal level, tool-less was correct on 35/40
versus 29/40 matched prompts. On paired discrimination it was
16/20 versus
11/20. These regime differences
are descriptive: the pilot was powered to detect ordered-channel behavior, not a
small performance difference between runtimes.

## Computational effort

| regime | condition | N | scheduled | completed | timeouts | tool users | median seconds | median input* | median output* | median reasoning* | emitted reasoning items* | model turns |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| tool_less | clean | 1 | 40 | 40 | 0 | 0 | 5.1 | 201 | 236 | 215 | 1 | 1 |
| tool_less | signal | 2 | 40 | 40 | 0 | 0 | 22.4 | 396 | 1700 | 1678 | 4 | 1 |
| tool_less | all_shuffled | 2 | 14 | 5 | 9 | 0 | 600.3 | 396 | 24215 | 24195 | 47 | 1 |
| codex_agent | clean | 1 | 40 | 40 | 0 | 0 | 12.9 | 13081 | 199 | 178 | 0 | 1 |
| codex_agent | signal | 2 | 40 | 40 | 0 | 3 | 28.8 | 13276 | 1125 | 1100 | 0 | 1 |
| codex_agent | all_shuffled | 2 | 14 | 11 | 3 | 14 | 750.1 | 401311 | 30151 | 23413 | 0 | 1 |

`*` Token and emitted-item medians use returned responses only. Nine disconnected
tool-less calls have no usage object. Codex input-token counts include its runtime
context and are not directly comparable to direct-API input counts.

Clean tool-less responses used a median 215 reasoning tokens and signal responses
1,678. The five completed controls used a median 24,195 reasoning tokens; all nine
other controls ran for about ten minutes without a response. The matched Codex
controls likewise drove tool use in 14/14 trials and much higher context/effort.
The intact lane therefore changed both correctness and computational tractability.

## Observable strategy boundary

Every tool-less trial was one independent Responses API request with `tools: []`,
`store: false`, and no prior-response context. Returned raw response objects are
preserved. They contain encrypted reasoning items with empty public summaries, so
their content cannot be inspected and no private-chain-of-thought claim is made.

The constrained payload tells successful subjects to emit only the answer. Accordingly,
zero final-text mentions of encoding among signal successes do not show a lack of
discovery. Two completed all-shuffled outputs explicitly said that ordering had been
scrambled. Strategy attribution for the tool-less successes remains indeterminate,
but it cannot involve the excluded shell/filesystem/tool mechanisms.

## Freeze, cost, and exclusions

The stopping boundary—r0001 through r0094—was frozen before response scoring or
inspection. It contains 94 scheduled trials: 40 clean, 40 signal, and 14 controls.
r0095 received `credit_balance_exhausted` before inference and is preserved as an
excluded invalid attempt. No later prompt was run and no timeout was retried.

The user reported approximately $20 billed. Returned usage objects yield only a
$7.5069 public-list-price lower bound; disconnected calls did not return usage
objects, so the repository cannot independently reconcile the billing total.

## Conclusion and next step

The reduced pilot answers the important mechanistic question efficiently: at N=2,
a tool-less GPT-5.6-Sol-xhigh invocation systematically followed which of two
equal-multiset ordered streams was intact. That rules out both bag-of-words inference
and a requirement for explicit Codex tool use as sufficient explanations.

Do not buy the remaining 226 planned calls. If one follow-up is run later, use a
small preregistered variable-stride test (for example 10 paired A/B seeds at fixed
periodic N=2 versus jittered spacing), with a hard dollar cap. That directly tests
whether periodic position is the exploitable cue and is more informative per dollar
than filling N=4, explanation, or additional all-shuffled cells.
