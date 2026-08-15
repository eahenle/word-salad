# Claims and evidence

## 1. Aggregate lexical content does not determine the response

- **Evidence:** Experiment 2 paired A/B stimuli have mechanically identical
  aggregate whitespace-word bags. At N=2, 19/40 pairs and 57/80 individuals
  tracked the intact order; at N=4, 8/40 pairs and 33/80 individuals did.
- **Controls:** 0/80 all-shuffled controls emitted either target answer; clean
  execution was 80/80.
- **Remaining alternatives:** model-specific priors, positional/coherence cues,
  explicit reconstruction, and runtime-specific behavior.
- **Allowed:** “Changing only embedded word order changed the model’s answer in
  the predicted direction.”
- **Not allowed:** “The model decodes arbitrary hidden messages.”

## 2. External agent tools are not required

- **Evidence:** Experiment 2’s direct, tool-less, cost-truncated N=2 pilot
  produced 35/40 expected answers and 16/20 complete pairs.
- **Controls:** sampled all-shuffled prompts produced no target A/B answer.
- **Remaining alternatives:** tool-less and Codex system contexts are not
  identical; this was a bounded pilot.
- **Allowed:** “Shell and filesystem tools are not necessary for N=2 recovery.”
- **Not allowed:** “All successes are purely one-pass transformer perception.”

## 3. Recovery does not require a fixed positional clock

- **Evidence:** Experiment 3’s 12-cell screen produced 69/240 fixed versus
  95/240 jitter expected answers and 17/120 versus 31/120 complete pairs.
  Selected-cell confirmation preserved recovery, with smaller carrier
  differences.
- **Controls:** matched seeds, masks, bags, and prompt lengths; small shuffled
  cohorts showed no target bias.
- **Remaining alternatives:** balanced jitter has burst/run structure.
- **Allowed:** “Recovery survived a nonconstant balanced-jitter carrier.”
- **Not allowed:** “Carrier geometry is irrelevant.”

## 4. Recovery survives uniformly random signal positions at 50% density

- **Evidence:** Experiment 4A: Sol-medium 30/40 individuals and 13/20 pairs;
  Terra-xhigh 16/40 and 5/20; aggregate 46/80 and 18/40.
- **Controls:** A/B prompts use the same uniformly sampled masks and identical
  bags; 0/10 all-shuffled controls emitted a target; 90/90 subjects completed.
- **Remaining alternatives:** 50% is not very sparse; only two model settings
  were tested; masks are random rather than adversarial.
- **Allowed:** “Recovery survived uniformly sampled placement without a fixed
  or designed interval schedule.”
- **Not allowed:** “The model can recover arbitrary subsequences at arbitrary
  dilution.”

## 5. Successful signal processing can be computationally cheap

- **Evidence:** all 46 successful Experiment 4A signal responses were observable
  direct one-pass, tool-free responses. Experiment 2 clean and successful N=2
  trials were much cheaper than many shuffled/N=4 reconstruction attempts.
- **Controls:** full emitted Codex traces and usage metadata were preserved.
- **Remaining alternatives:** private reasoning is unavailable; cached-input and
  runtime accounting are implementation-specific.
- **Allowed:** “Many successes occurred without observable iterative decoding or
  tool use.”
- **Not allowed:** “The model was unaware of the encoding.”

## 6. The effect is model/configuration specific

- **Evidence:** Experiment 3 showed Sol strongest, Terra/Luna intermediate, and
  Spark at essentially zero complete-pair recovery across efforts.
- **Controls:** common frozen prompt cohort across exact configurations.
- **Remaining alternatives:** four proprietary model families do not define a
  population; effort effects were nonmonotonic.
- **Allowed:** “Recovery varied substantially across the tested model families.”
- **Not allowed:** “Capability scales universally with model size or reasoning.”

## 7. Low-density naturalistic generalization is not established

- **Evidence:** 4C and 4C.1 each produced 0/6 expected answers and 0/3 pairs.
  Later density tasks exposed target-salience, task-validation, and target-space
  problems.
- **Allowed:** “The 50%-density result did not straightforwardly generalize to
  ~7.4% natural coherent carriers.”
- **Not allowed:** “Foreground coherence alone suppresses recovery.”

## Global interpretation boundary

The data establish behavioral sensitivity to embedded linguistic order. They do
not establish a particular attention mechanism, explicit demultiplexing, prompt
injection exploitability, universality across LLMs, or recovery at arbitrary
density.
