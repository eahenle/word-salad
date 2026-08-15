# Publication readiness and stop decision

## Decision

The exploratory experimental phase is complete. The strongest defensible result
is already supported by a progressive chain of frozen controls:

> GPT-5.6-Sol is behaviorally sensitive to coherent linguistic order embedded
> in lexically matched interference, including when paired stimuli have the same
> aggregate word bag and signal positions are uniformly random.

This is a model- and runtime-specific behavioral result. It is not a claim about
a particular transformer mechanism, arbitrary hidden subsequences, or practical
prompt-injection exploits.

## Why the evidence is sufficient to draft

1. Experiment 1C hardened isolation and reduced surface-cue explanations.
2. Experiment 2 held aggregate lexical content constant while answer identity
   tracked the intact ordered lane; all 80 shuffled controls avoided both target
   answers.
3. A direct tool-less pilot recovered 16/20 complete N=2 A/B pairs, showing that
   shell and filesystem tools were unnecessary for that condition.
4. Experiment 3 preserved recovery under nonconstant balanced jitter and exposed
   a strong tested-model-family boundary.
5. Experiment 4A preserved recovery under uniformly random 161-of-322 signal
   placement: 18/40 complete pairs and 46/80 expected individual answers, with
   0/10 shuffled target answers.

Together these results remove the main bag-of-words, tool-use, fixed-clock, and
designed-carrier alternatives without claiming an internal mechanism.

## Publication-closing instrument check

Experiment 6 was intended to clarify the lower-density boundary with a larger
output space. Its preregistered gates worked as safeguards:

- v1 rotation task: 0/40 clean exact; frozen and abandoned.
- v2 positional-swap task: 40/40 clean exact.
- v2 shuffled N=1 controls: 2/10 exact target-A outputs.
- no v2 25% or 50% carrier prompt was generated or run.

The v2 control result shows that the model's outputs are not uniform over the
nominal 5! state space. Exact target A appeared without preservation of the
intended complete A/B ordering, making the wording unsuitable as an
order-specific measurement instrument. This is a successful preregistered
instrument check, not a negative carrier result. Per the stop rule, the task
will not be redesigned again.

## Remaining limitations, not drafting blockers

- The strongest evidence concerns proprietary GPT-5.6-Sol configurations.
- Uniform-random recovery was tested at 50% signal density; general recovery at
  substantially lower densities remains unresolved.
- Natural coherent foregrounds at approximately 7.4% produced null results.
- There is no human readability baseline using the exact frozen stimuli.
- The experiments establish behavior, not a neural mechanism.
- An external lab has not yet independently replicated the result.

These limitations belong in the manuscript and motivate follow-up work. None
invalidates the equal-bag A/B result or requires another internal experiment
before drafting.

## Recommended next action

Draft the manuscript from the frozen evidence package. Seek independent
replication on the committed prompt cohorts before or during peer review. Do not
resume task redesign unless reviewers identify a specific gap that changes the
central claim.
