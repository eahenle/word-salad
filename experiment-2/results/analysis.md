# Experiment 2 analysis

This report treats answer identity as the primary endpoint. A signal A trial is
successful only when it produces answer A, and likewise for B. All-shuffled
outputs are reported as answer bias rather than generic correctness.

## Main result

The aggregate word multiset was mechanically identical within every paired A/B
stimulus. Changing only the intact lane's order nevertheless changed the answer in
the predicted direction for 19/40 paired seeds at N=2 and
8/40 at N=4. Signal answer success was
57/80 at N=2 and
33/80 at N=4. Clean
execution was 80/80. The 80 all-shuffled controls produced zero A or B target answers.

This is affirmative behavioral evidence that ordered relational information in the
sparse stream affected the model's output; unordered lexical content alone cannot
explain the paired A/B result. It does not by itself identify the internal mechanism.

## Answer identity

| arm | condition | N | stimulus | trials | A | B | other | expected |
| --- | --- | ---: | --- | ---: | ---: | ---: | ---: | ---: |
| constrained | all_shuffled | 2 | none | 20 | 0 | 0 | 20 | 0 |
| constrained | all_shuffled | 4 | none | 20 | 0 | 0 | 20 | 0 |
| constrained | clean | 1 | A | 20 | 20 | 0 | 0 | 20 |
| constrained | clean | 1 | B | 20 | 0 | 20 | 0 | 20 |
| constrained | signal | 2 | A | 20 | 15 | 0 | 5 | 15 |
| constrained | signal | 2 | B | 20 | 1 | 14 | 5 | 14 |
| constrained | signal | 4 | A | 20 | 9 | 0 | 11 | 9 |
| constrained | signal | 4 | B | 20 | 0 | 12 | 8 | 12 |
| explanation | all_shuffled | 2 | none | 20 | 0 | 0 | 20 | 0 |
| explanation | all_shuffled | 4 | none | 20 | 0 | 0 | 20 | 0 |
| explanation | clean | 1 | A | 20 | 20 | 0 | 0 | 20 |
| explanation | clean | 1 | B | 20 | 0 | 20 | 0 | 20 |
| explanation | signal | 2 | A | 20 | 16 | 0 | 4 | 16 |
| explanation | signal | 2 | B | 20 | 2 | 12 | 6 | 12 |
| explanation | signal | 4 | A | 20 | 8 | 0 | 12 | 8 |
| explanation | signal | 4 | B | 20 | 0 | 4 | 16 | 4 |

## Scheduled- and completed-response signal sensitivity

Scheduled-trial denominators are primary; the completed-response column shows
the effect of the fixed 900-second subject timeout.

| arm | N | trials | expected | scheduled rate | completed | expected/completed | timeouts | counterpart answer |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| constrained | 2 | 40 | 29 | 72.5% | 40 | 29/40 | 0 | 1 |
| constrained | 4 | 40 | 21 | 52.5% | 33 | 21/33 | 7 | 0 |
| explanation | 2 | 40 | 28 | 70.0% | 40 | 28/40 | 0 | 2 |
| explanation | 4 | 40 | 12 | 30.0% | 36 | 12/36 | 4 | 0 |

## Paired A/B discrimination

| arm | condition | N | pairs | A→A and B→B | rate [95% Wilson CI] |
| --- | --- | ---: | ---: | ---: | ---: |
| constrained | clean | 1 | 20 | 20 | 1.000 [0.839, 1.000] |
| constrained | signal | 2 | 20 | 11 | 0.550 [0.342, 0.742] |
| constrained | signal | 4 | 20 | 5 | 0.250 [0.112, 0.469] |
| explanation | clean | 1 | 20 | 20 | 1.000 [0.839, 1.000] |
| explanation | signal | 2 | 20 | 8 | 0.400 [0.219, 0.613] |
| explanation | signal | 4 | 20 | 3 | 0.150 [0.052, 0.360] |

## Computational effort

| arm | condition | N | trials | timeouts | tool users | median seconds | median input | median reasoning |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| constrained | all_shuffled | 2 | 20 | 5 | 19 | 724.4 | 401311 | 23413 |
| constrained | all_shuffled | 4 | 20 | 5 | 15 | 617.9 | 278183 | 19988 |
| constrained | clean | 1 | 40 | 0 | 0 | 12.9 | 13081 | 178 |
| constrained | signal | 2 | 40 | 0 | 3 | 28.8 | 13276 | 1100 |
| constrained | signal | 4 | 40 | 7 | 24 | 459.5 | 179551 | 12030 |
| explanation | all_shuffled | 2 | 20 | 1 | 17 | 440.0 | 278065 | 15009 |
| explanation | all_shuffled | 4 | 20 | 4 | 14 | 551.3 | 277257 | 15880 |
| explanation | clean | 1 | 40 | 0 | 0 | 12.8 | 13059 | 202 |
| explanation | signal | 2 | 40 | 0 | 9 | 35.9 | 13232 | 1311 |
| explanation | signal | 4 | 40 | 4 | 28 | 449.7 | 161001 | 14424 |

Across the full slate, 26/320 subjects reached the fixed timeout. Clean
trials used no tools. By contrast, all-shuffled subjects used tools in 65/80
trials and N=4 signal subjects used tools in 52/80 trials.

## Independently reviewed observable strategies

The condition-aware trace audit covered all 170 semantic successes, all 108
automatic explicit-stride classifications, and 28 additional stratified
failures/controls (269 unique trials). It required concrete every-nth/residue
evidence for a fixed-stride label; generic mentions of shuffling or interleaving
were insufficient.

| reviewed strategy among 90 signal successes | trials |
| --- | ---: |
| direct_one_pass_tool_free_response | 58 |
| explicit_fixed_stride_recognition_or_testing | 23 |
| indeterminate | 1 |
| repeated_reconstruction | 5 |
| shell_or_tool_assisted_lexical_reconstruction_without_stride | 3 |

Concrete fixed-stride behavior was observable in 23/90 successful signal
traces and 19/59 audited controls. A direct one-pass,
tool-free response was observable in 58/90 signal successes. Only
2/90 correct signal final responses spontaneously mentioned shuffling or encoding;
that silence is not evidence against discovery, particularly in the constrained arm.

The independent review corrected 68/269 normalized automatic strategy labels.
Only 42/108 automatically flagged explicit-stride traces contained concrete
stride evidence, so the reviewed labels—not the regex heuristic—are authoritative.

## Unexpected behaviors

- The wrong counterpart answer appeared three times on B stimuli; the reverse
  A-to-B error never appeared. This indicates a modest answer-A asymmetry.
- Explanation permission did not improve recovery. Its N=4 signal rate was
  12/40 versus 21/40 for constrained output.
- Controls frequently recognized corruption and launched long reconstruction
  attempts, yet none produced either target answer.
- Correct N=2 signal responses were usually cheap and tool-free, whereas N=4
  successes mixed direct responses with explicit or repeated reconstruction.

## Isolation, invalid attempts, and tool-less regime

The integrity audit passed all 320 active outcomes. Nine first attempts were
rejected before inference by an account usage cap, archived byte-for-byte, and
rerun with the exact same prompt hashes after an independent capacity probe.
There were no broken-pipe, transport, controller, nonzero-exit, or missing-final
failures eligible for retry. Twenty-six subject timeouts remain outcomes.

Post-slate trace review found 22 environment-probe attempts but zero observable
host access and zero direct experiment-context leaks. Same-host container isolation
is a strong audited practical boundary, not a cryptographic multi-host guarantee.

The exact tool-less GPT-5.6-Sol-xhigh comparison subsequently ran as a
cost-truncated pilot. Its stopping boundary was frozen before scoring: 94
scheduled prompts, 85 completed responses, and nine accepted approximately
600-second timeout/nonresponses. r0095 returned `credit_balance_exhausted`
before inference and was excluded; no later prompt was run and no alternate
model or Codex credential was substituted.

On the 40 N=2 signal prompts, tool-less invocations produced 35 expected answers
and 16/20 paired A/B discriminations. The same Codex prompts produced 29/40 and
11/20, respectively. This shows that shell/filesystem tools and an agentic
command loop are not required for the ordered-lane behavior. See
`raw-model-pilot-analysis.md` for the audited matched comparison and its limits.

## Conclusion and next experiment

Experiment 2 supports the preregistered behavioral claim: with aggregate lexical
content held exactly constant, the identity of the intact ordered lane systematically
changed the model's answer. Recovery was reliable but imperfect at N=2 and weakened
substantially at N=4. The zero-target all-shuffled result argues against unordered
bag-of-words inference as the source of the paired effect.

The full 320-call tool-less slate should not be resumed. The strongest next
discriminator per dollar is a small preregistered paired experiment comparing
fixed periodic spacing with jittered spacing. Do not interpret tool-less success
as proof of a unique internal mechanism: system contexts differ, private
reasoning remains unavailable, and this is one model/runtime.

Behavioral correctness and observable trace strategy are separate outcomes. No claim
about private internal reasoning is made.
