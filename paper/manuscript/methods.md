# Methods

## Study scope and experimental progression

We evaluated whether a language model could use the order of a coherent word
sequence embedded in lexically matched interference. The program progressed
through preregistered or prospectively frozen studies that removed successively
stronger alternative explanations. Experiment 1C hardened execution isolation
and tested surface normalization. Experiment 2 introduced paired payloads with
identical aggregate word multisets but different operation order and answer
keys. A subsequent tool-less pilot repeated the principal N=2 condition.
Experiment 3 compared fixed and balanced-jitter carriers across model and
reasoning configurations. Experiment 4A sampled signal positions uniformly
without replacement. Later low-density and natural-prose studies characterized
limits and measurement problems rather than serving as evidence required for
the central claim.

Each active dataset was frozen before analysis or before the next experimental
stage. Historical same-host runs, infrastructure-rejected attempts, and failed
measurement instruments were retained separately rather than overwritten. The
publication evidence layer is identified by Git tag
`paper-evidence-freeze-v1`.

## Payloads and deterministic state tasks

The core payloads described a three-object state-transition task involving a
brass key, silver coin, and glass marble placed in labeled boxes. Subjects had
to execute a sequence of moves, content swaps, and label swaps and report the
final labeled location of all three objects. A deterministic simulator produced
the answer key.

Experiment 2 constructed payloads A and B from the same operation sentences in
different, noncommuting orders. The payloads contained 161 whitespace-delimited
words each and satisfied exact multiset equality:

```text
Counter(payload_A.split()) == Counter(payload_B.split())
```

The operation orders produced different deterministic answers. Payload A ended
with the brass key in green, silver coin in blue, and glass marble in green;
payload B differed only in placing the silver coin in red. Requiring all three
assignments made answer identity directly scorable. The same paired payloads
were reused in Experiments 3 and 4A.

## Multiplex construction and equal-bag controls

Payload words were represented internally by source-word indices. In a signal
stimulus, one sequence of indices preserved payload A or B order, while the
interference stream was a deterministic random permutation of the same source
word multiset. Paired A/B prompts shared the same signal carrier, interference
permutation, length, phase where applicable, and complete aggregate word bag.
Only the order assigned to signal positions differed. Mechanical validation
checked prompt lengths, source-index permutations, signal extraction, paired
bag equality, and the absence of an intact A or B payload in controls.

All-shuffled controls preserved the lexical ingredients and prompt geometry but
contained no intact A or B ordering. These controls measured target production
available from unordered lexical content, model priors, or reconstruction that
did not require the intended complete signal order.

Experiment 2 used two lane counts. At N=2, 161 ordered signal words and 161
interference words yielded a 322-word prompt and 50% signal density. At N=4,
the signal constituted one of four 161-word lanes, yielding 644 words and 25%
signal density. Each arm contained clean A/B trials, signal A/B trials, and
all-shuffled controls. Constrained-output and explanation-permitted payload
arms had equal-bag A/B construction within arm.

## Carrier geometries

Three N=2 carrier geometries were studied.

**Fixed.** Signal and distractor positions alternated at period two, with phase
counterbalanced by the generator.

**Balanced jitter.** The signal order and 50% density were preserved while the
constant clock was removed. For each 161-word payload, signal-to-signal
intervals were a seed-permuted balanced collection of short and long gaps. A/B
pairs shared the same mask and distractor permutation.

**Uniform random.** Experiment 4A sampled exactly 161 distinct positions
uniformly without replacement from `range(322)`, sorted them, and filled them
with successive payload words. The remaining 161 positions received the
matched distractor stream. No mask was rejected based on edge position, run
length, adjacency, gap variance, or apparent local structure. Paired A/B
prompts used identical masks. Thus each prompt contained 161 signal words, 161
distractor words, and 322 total positions at 50% density.

## Models and execution regimes

The principal subjects were GPT-5.6-Sol Codex agents. Experiment 1C and
Experiment 2 used reasoning level `xhigh`. Experiment 4A used GPT-5.6-Sol at
`medium` and GPT-5.6-Terra at `xhigh`. Experiment 3 screened GPT-5.6-Sol,
GPT-5.6-Terra, GPT-5.6-Luna, and GPT-5.3-Codex-Spark at `medium`, `high`, and
`xhigh`, with no substitution for unavailable configurations.

Each Codex trial used a fresh ephemeral subject. The stimulus was the only
user-level content; subjects were not told that the prompt was multiplexed,
shuffled, encoded, or intended as a puzzle. No trial shared a conversation with
another trial. The runtime's default system/developer context remained present,
but experiment descriptions, source files, metadata, answer keys, prior
responses, and filenames were excluded from subject context.

The hardened Codex runs in Experiments 1C–4A used pinned image
`sha256:883e4d8d659d28c25d2473c0dec9ff43d1bafb7ce3920ada270627df3c202402`.
Each container had a read-only image and fresh tmpfs mounts, no repository or
host temporary-directory mount, and no prior Codex session. The boundary was
validated adversarially before execution. Same-host Docker is an audited
practical isolation boundary, not a cryptographic multi-host guarantee.

Codex tools remained available in the principal agent studies so observable
tool use could be measured. A separate Experiment 2 pilot submitted the exact
N=2 prompts through a direct tool-less GPT-5.6-Sol-xhigh invocation with no
shell, filesystem, browser, MCP, or agentic command loop. That pilot stopped at
a prospectively frozen direct-cost boundary; unavailable responses were not
replaced with another model.

## Trial execution and trace preservation

Codex trials used a 900-second subject timeout and four workers in the main
hardened slates. Timeouts after inference began were retained as scheduled-trial
outcomes. An attempt was retry eligible only after a mechanically documented
pre-response infrastructure failure, such as an authentication, capacity,
transport, controller, or missing-final-message failure. The rejected attempt
was archived, and only the exact affected prompt could be rerun. Correctness or
strategy was never a retry criterion.

For every Codex trial, the harness preserved full emitted stdout JSONL, stderr,
exit status, timeout state, elapsed wall time, thread identifier, exposed usage
metadata, tool events, shell commands, and final agent response. Private chain
of thought was not available and is not claimed. Observable strategy categories
were assigned only from emitted events and final text.

## Surface normalization

Experiment 1C used a 2×2 surface matrix: original text, Unicode lowercase,
Unicode punctuation-category removal, and both transformations. Punctuation
removal deleted characters in Unicode general categories beginning with `P`.
Normalization changed only lexical rendering; source-index geometry, phase,
and lane permutations were paired across variants. Signal extraction and lane
multisets were revalidated after rendering.

## Endpoints and scoring

For the equal-bag A/B studies, the primary endpoint was complete paired
discrimination: both members of a matched seed had to produce their respective
full answer A and answer B. Expected individual answer recovery was secondary.
All-shuffled target production, counterpart answers, malformed assignments,
timeouts, and other outputs were retained separately.

Responses were first scored automatically and then audited under the procedures
frozen for each study. Semantic scoring required all three object assignments
to match the deterministic state. Strict exact-string metrics were retained
separately where available. Strategy auditing was behaviorally independent of
answer scoring: a correct answer could be direct, explicit-stride, repeated
reconstruction, tool assisted, or indeterminate.

## Statistical analysis

All primary rates use scheduled-trial denominators. We report exact
numerator/denominator, percentage, and Wilson 95% confidence interval. Matched
carrier comparisons use discordant prompt counts and two-sided exact McNemar
tests where prospectively specified in the frozen analysis. These statistics
describe repeatability for fixed prompts, models, and runtimes; the models are
not a random sample from a model population.

Computational outcomes include elapsed time, exposed reasoning/output usage,
tool-call count, shell-call count, and timeout frequency. Medians use the
available runtime usage values under the rules recorded by each experiment.

## Integrity and publication audit

Prompt hashes and generator metadata were frozen before inference. Responses
were frozen before scoring. The publication builder regenerates six result
figures and six machine-readable tables from committed frozen sources. A
fail-closed consistency checker independently derives the cited Experiment
1C–6 counts and validates publication-facing geometry and language. At the
evidence freeze, all 43 checks passed. The evidence manifest records SHA-256
hashes for claims, tables, figures, analysis scripts, and source summaries.

## Boundary studies and stopping rule

Natural coherent covers at approximately 7.4% density and matched foreground
decoherence produced no complete A/B pair. Later density studies encountered
task-readout contamination and execution ambiguity. A publication-closing
five-symbol task was therefore required to pass clean execution and shuffled
controls before any noisy carrier trial. Version 1 failed clean execution and
was frozen. Version 2 passed clean execution but emitted target A in 2/10
independently shuffled controls. Under the preregistered rule, no buried-signal
trial using that instrument was generated or run, and internal experimental
expansion ended.
