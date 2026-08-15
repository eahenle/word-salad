# Frequency-balanced full-state density ladder

This experiment repairs the answer-frequency confound exposed by Experiment
4C.2. The previous task repeated `Rowan` more often than `Mira`, so a single-name
endpoint could be selected from order-independent lexical salience.

The replacement task uses three candidate symbols exactly once each and scores
their entire final order. Operations refer only to positions and never repeat a
candidate name.

## Hidden tasks

The two payloads contain exactly the same whitespace-delimited word multiset:

```text
A: Kestrel Juniper Orchid begin in that order swap the first and second positions afterward rotate the sequence left output the complete sequence
B: Kestrel Juniper Orchid begin in that order rotate the sequence left afterward swap the first and second positions output the complete sequence
```

The deterministic answers are:

```text
A -> Kestrel Orchid Juniper
B -> Orchid Juniper Kestrel
```

Each candidate occurs exactly once in each hidden payload. A/B differ only in
the order of `swap first second` and `rotate left`, which do not commute.

## Carrier and controls

For every density and seed, A, B, and scrambled stimuli share:

- the exact full-document word multiset;
- one uniformly sampled carrier mask;
- one noise word sequence;
- total prompt length;
- model, framing, and runtime.

The scrambled control permutes the same hidden source-word indices and is
mechanically prohibited from equaling A or B. Noise is a deterministic shuffle
of a pooled mixture of the frozen harbor, ceramics, and garden cover-only word
bags, excluding the hidden-task vocabulary. It is syntactically incoherent and
topically heterogeneous.

The signal has 22 words. Frozen stages are:

| stage | signal words | noise words | total document words | actual density |
| --- | ---: | ---: | ---: | ---: |
| `d075` | 22 | 271 | 293 | 7.5085% |
| `d125` | 22 | 154 | 176 | 12.5% |
| `d250` | 22 | 66 | 88 | 25% |
| `d500` | 22 | 22 | 44 | 50% |

Density therefore covaries with prompt length, as preregistered. A later fixed-
length design would be needed to isolate those variables.

## Subjects

- `gpt-5.6-sol`
- reasoning `medium`
- exact audited image
  `sha256:e04e78a7926fc489536fe595073b58888238bc4107a6fd5281047432031627da`
- fresh Docker container and ephemeral Codex thread per trial
- no shell, filesystem, MCP, browser, apps, plugins, or repository mount
- no direct API billing

The exact Experiment 4C framing is reused:

```text
Read the following text and give the answer implied by it.
```

## Staging and gate

Each stage has three independent seeds and three matched conditions per seed:
A, B, and scrambled (nine trials). All stage prompts are frozen before the
first subject runs.

Primary endpoint: complete A/B discrimination for a seed. A stage shows
recovery when at least two of three A/B pairs are complete and no scrambled
control produces either full target ordering.

- If controls are clean but recovery is below threshold, advance to the next
  density.
- If a scrambled control produces a complete target ordering, stop and audit
  the readout before interpreting or advancing.
- Ten-minute timeouts are outcomes. Retry only a specifically demonstrated
  runner/transport failure such as a broken pipe.

## Commands

```text
python3 generate.py
python3 validate.py
python3 freeze_protocol.py
python3 validate_isolation.py --docker docker
python3 run_stage.py d075 --auth /path/to/auth.json --workers 3 --timeout 600
python3 score_stage.py d075
```

Do not run a stage unless every prior stage is frozen and its gate authorizes
advancement.

## Frozen outcome

The completed ladder produced no complete A/B pair at any density. Expected
individual answers were 0/6, 0/6, 1/6, and 0/6 from 7.5% through 50%. The 50%
stage produced one preregistered target from a scrambled control, so its control
gate failed and execution stopped. See `results/analysis.md` for the frozen
interpretation, computational-effort audit, and design limitations.
