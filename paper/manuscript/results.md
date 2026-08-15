# Results

## Hardened replication preserved signal recovery while shuffled performance remained near floor

Experiment 1C scheduled 320 GPT-5.6-Sol-xhigh trials across four surface forms,
two conditions, and N=1, 2, 4, and 8. In the original-surface replication,
semantic success was 22/40 signal trials and 0/40 all-shuffled controls. Across
all four surface variants, signal success was 80/160, compared with 2/160 in
all-shuffled controls. By variant, signal recovery was 22/40 original, 18/40
lowercase, 22/40 without punctuation, and 18/40 lowercase without punctuation;
the corresponding shuffled counts were 0/40, 1/40, 1/40, and 0/40.

The preregistered normalization interaction hypothesis was not supported.
Removing case or punctuation did not selectively reduce shuffled reconstruction
because the hardened original shuffled condition was already at floor, and
normalization often reduced signal recovery as much or more. Surface cues were
therefore not established as the cause of the intact-signal effect.

Difficulty was visible in computational outcomes. Across variants, signal
trials produced 11/160 timeouts and observable tool use in 45/160 trials;
all-shuffled trials produced 30/160 timeouts and tool use in 100/160. The
direction of this effort asymmetry motivated answer-identity controls that did
not depend on a generic success judgment.

## Equal aggregate word bags produced different answers when embedded order changed

Experiment 2 held the complete whitespace-word multiset exactly constant within
each paired A/B stimulus. Clean task execution was 80/80. At N=2, the expected
full answer occurred in 57/80 signal trials (71.3%, Wilson 95% CI 60.5–80.0%)
and both members were correct in 19/40 paired seeds (47.5%, 32.9–62.5%). At
N=4, expected full answers occurred in 33/80 trials (41.3%, 31.1–52.2%) and
8/40 complete pairs (20.0%, 10.5–34.8%). None of the 80 all-shuffled controls
produced either target A or target B (0%, 95% CI 0–4.6%).

Because paired A and B prompts had identical aggregate lexical content,
different expected answers, and matched interference geometry, the paired
result cannot be explained by the aggregate word bag identifying an answer.
The result establishes behavioral sensitivity to the preserved ordering under
these conditions; it does not identify how the model found that ordering.

The two output arms did not show an advantage from explanation permission. At
N=2, constrained and explanation-permitted signal recovery was 29/40 and 28/40,
respectively. At N=4 it was 21/40 and 12/40. The primary reported totals retain
both prospectively defined arms rather than selecting the stronger one.

## A direct tool-less pilot replicated N=2 answer-identity tracking

The cost-truncated direct-invocation pilot repeated the 40 N=2 signal prompts
with GPT-5.6-Sol-xhigh and no tools or agentic command loop. It produced 35/40
expected full answers (87.5%, Wilson 95% CI 73.9–94.5%) and 16/20 complete A/B
pairs (80.0%, 58.4–91.9%). No target answer appeared in the sampled shuffled
controls. The exact direct-invocation control cohort was cost truncated: 14
controls were scheduled, nine timed out or did not complete, and five completed.

These observations show that shell, filesystem, and an iterative Codex tool
loop were not necessary for N=2 recovery. Differences between the direct and
Codex system contexts prevent treating the pilot as a fully symmetric runtime
comparison.

## Recovery survived removal of a fixed positional clock

Experiment 3 applied a common ten-pair fixed/jitter screen to 12 model-by-effort
configurations. Across those fixed conditions, expected answers occurred in
69/240 trials (28.8%, Wilson 95% CI 23.4–34.8%) and 17/120 complete pairs
(14.2%, 9.0–21.5%). Under balanced jitter, the corresponding counts were
95/240 (39.6%, 33.6–45.9%) and 31/120 (25.8%, 18.8–34.3%). The matched
screening comparison contained 24 fixed-only and 50 jitter-only individual
successes (two-sided exact McNemar p=.0034), and 8 fixed-only versus 22
jitter-only paired successes (p=.0161). Thus breaking the period-two clock did
not reduce aggregate screening recovery; in this cohort, jitter recovery was
higher.

All 36 small all-shuffled controls across the model/reasoning screen avoided
both target answers. Fresh confirmation seeds were run only for three whole
cells selected after the screening cohort froze: Sol-medium, Terra-xhigh, and
Spark-xhigh. In confirmation, Sol-medium yielded 6/10 complete pairs under
both fixed and jitter carriers; Terra-xhigh yielded 2/10 fixed and 3/10 jitter;
Spark-xhigh yielded 0/10 under either carrier. The confirmation-only fixed and
jitter difference was not distinguishable in the matched analysis.

## Uniform random signal placement preserved recovery at 50% density

Experiment 4A removed both a fixed stride and the balanced-jitter interval
schedule. Each prompt placed 161 ordered signal words into 161 positions
sampled uniformly without replacement from 322 positions and filled the other
161 positions with the matched distractor stream. No masks were rejected based
on their run or edge structure.

Sol-medium produced 30/40 expected individual answers and 13/20 complete A/B
pairs. Terra-xhigh produced 16/40 and 5/20. Aggregated across the two
prospectively selected configurations, uniform recovery was 46/80 individuals
(57.5%, Wilson 95% CI 46.6–67.7%) and 18/40 pairs (45.0%, 30.7–60.2%). All ten
shuffled controls avoided both targets (0%, 95% CI 0–27.8%), and all 90
scheduled subjects completed without timeout or runner error.

For the same two configurations over 20 matched seeds, fixed, balanced-jitter,
and uniform paired results were 12/40, 18/40, and 18/40, respectively. Relative
to balanced jitter, the uniform comparison had 9 jitter-only and 9 uniform-only
paired successes (two-sided exact McNemar p=1.0); the individual comparison had
18 jitter-only and 15 uniform-only successes (p=.728). The result does not show
that geometry is irrelevant, but it rules out a fixed clock or the particular
balanced-jitter schedule as necessary conditions in this 50%-density regime.

All 46 successful Experiment 4A signal responses were observable direct,
one-pass, tool-free responses in the emitted trace. This category describes the
recorded runtime events; it does not establish an absence of unobserved internal
reasoning.

## Recovery varied more clearly by tested model family than by reasoning setting

In the common Experiment 3 screen, Sol was the strongest tested family. Across
its three effort settings, it produced 32/60 fixed and 49/60 jitter expected
answers, with 12/30 and 19/30 complete pairs. Terra produced 16/60 fixed and
24/60 jitter answers, with 1/30 and 7/30 pairs. Luna produced 21/60 under each
carrier, with 4/30 fixed and 5/30 jitter pairs. Spark produced 0/60 fixed and
1/60 jitter expected answers and no complete pair.

Reasoning effort was not monotonically related to recovery within families.
For example, some medium settings exceeded high or xhigh settings on the same
common prompts. These fixed-condition comparisons establish heterogeneity among
the tested configurations; they do not support population-level scaling claims
over model size or reasoning effort.

## Signal availability was associated with lower observable computational effort

Experiment 2's constrained arm showed a pronounced effort gradient. Median
exposed reasoning tokens were 178 for clean N=1, 1,100 for signal N=2, 12,030
for signal N=4, 23,413 for all-shuffled N=2, and 19,988 for all-shuffled N=4.
Tool use occurred in 0/40 clean, 3/40 signal N=2, 24/40 signal N=4, 19/20
shuffled N=2, and 15/20 shuffled N=4 trials. The respective timeout counts were
0/40, 0/40, 7/40, 5/20, and 5/20.

These outcomes distinguish cheap behavioral recovery from expensive failed
search in many controls. They do not imply that all direct successes used the
same mechanism. An independent trace review found 58 observable one-pass,
tool-free responses among 90 Experiment 2 signal successes, while 23 successful
traces contained concrete fixed-stride recognition or testing.

## Substantially sparser and naturalistic carriers remained unresolved

At approximately 7.4% density, Experiment 4C's coherent natural foreground
produced 0/6 expected hidden answers and 0/3 complete pairs, with 0/6 control
target selections. Experiment 4C.1 permuted only nonsignal words while
preserving signal words, positions, order, prompt length, and the full word bag;
it also produced 0/6 expected answers, 0/3 pairs, and 0/3 scrambled targets.
Destroying foreground syntax was therefore insufficient to recover that
low-density stream.

A later balanced-density task produced no complete pair at 7.5%, 12.5%, 25%,
or 50%. One of six individual signal trials was correct at 25%, while a
scrambled control produced a target at 50%. Because that task had not first
established a strong clean-execution and shuffled-control instrument, these
results do not define a density threshold.

The publication-closing Experiment 6 applied prospective instrument gates.
Version 1 returned 0/40 correct clean executions and was frozen before controls.
Version 2 returned 40/40 clean executions, but exact target A appeared in 2/10
independently shuffled N=1 controls. The shuffled controls therefore revealed a
target-producing pathway that did not require preservation of the intended
complete A/B ordering. The task was abandoned as an order-specific measurement
instrument, and no buried-signal trial using it was generated or run.

## Audits did not support the tested local or Codex-history contamination pathways

The frozen subject image and an independently clean rebuild contained no
observable project-specific memory, AGENTS file, Codex history, session,
configuration, prompt artifact, or project file. Five fresh sterile subjects
were then asked for high-entropy values stored only in prior Codex cloud
history. Exact recovery was 0/5, every subject returned `UNKNOWN`, and five
matched nonexistent or unstored controls also returned `UNKNOWN`.

A separate keyword audit of 1,709 frozen traces found that reconstruction or
interleaving language overwhelmingly occurred in visibly scrambled or
multiplexed prompts. Ordinary coherent Experiment 4C prose was positive in
0/12 traces, and unrelated contamination probes in 0/5. These audits provide no
evidence for the tested local-image or Codex-history leakage pathways. They do
not rule out every possible upstream context mechanism.

## Summary of established and unresolved results

Across equal-bag A/B stimuli, changing which embedded order was coherent changed
GPT-5.6-Sol's answer in the predicted direction above matched shuffled controls.
The behavior survived tool removal, balanced jitter, and uniformly random
50%-density placement. It varied substantially across tested model families.
The mechanism, minimum density, recovery within coherent natural foregrounds,
human readability, and generality to other model systems remain unresolved.
