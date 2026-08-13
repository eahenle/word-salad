# Experiment 2: paired equal-multiset ordered payloads

This experiment tests whether changing only the ordering of one coherent sparse
stream changes GPT-5.6-Sol-xhigh's answer. Payloads A and B use the same six
operation sentences and exactly the same whitespace-delimited word multiset;
only operations 5 and 6 exchange positions. A deterministic state simulator
validates that their final answers differ.

The protocol is staged after the frozen, hardened Experiment 1C dataset. Its
primary endpoint is answer identity: A-like versus B-like output, not generic
success. Signal conditions used N=2 and N=4, with identical phase,
distractor index permutations, prompt length, and aggregate bag of words for
each paired seed. Clean A/B validate task execution. All-shuffled prompts
measure residual answer bias.

Two output arms were run: constrained final-answer only and explanation
permitted. The latter requests a brief account without mentioning ciphers,
interleaving, strides, or hidden messages. Codex-agent trials retain the pinned
hardened container and full raw traces. A tool-less GPT-5.6-Sol-xhigh regime
was then run with a project-local ignored API key. It was frozen as a
cost-truncated pilot at a boundary chosen before scoring: r0001--r0094,
comprising 85 completed responses and nine accepted 600-second
timeout/nonresponses. r0095 returned `credit_balance_exhausted` before inference
and was excluded. No model substitution was made, no later prompt was run, and
no further API spending is authorized.

Generate and validate payloads with:

```bash
python3 -B experiment-2/simulate.py
```

Answer keys exist only in coordinator-side simulation output/results and must
never be mounted or sent into subject containers.

## Pilot freeze

The seed-1 pilot completed clean A/B, N=2 signal A/B, and N=2 all-shuffled
trials in both arms. Its artifact audit passed and no host or experiment-context
leakage was observed. See `results/pilot-report.md`. The protocol was frozen
without modification before launching the remaining 20-seed N=2/N=4 slate.

## Completed Codex-agent slate

The full Codex-agent run temporarily stopped when an account usage cap rejected
the final nine subjects before inference. Their failed attempts were archived,
capacity was verified independently, and the exact nine stimuli were rerun.
The active dataset now contains 320/320 outcomes and passes the full integrity
and leakage audits. See `results/partial-slate-status.md`,
`results/quota-rerun-resolution.json`, and `results/integrity-audit.json`.

The two arms each contain:

- 20 clean A and 20 clean B trials;
- 20 signal A and 20 signal B trials at each of N=2 and N=4;
- 20 all-shuffled controls at each of N=2 and N=4.

The paired A/B prompts have exactly equal aggregate whitespace-delimited word
multisets, identical signal phase, and byte-identical distractor lanes. Only the
ordering of the intact sparse stream differs.

## Results

Clean execution succeeded in 80/80 trials. Across both arms, signal answer
identity was correct in 57/80 trials at N=2 and 33/80 at N=4. Both members of a
paired seed produced their respective expected A and B answers in 19/40 N=2
pairs and 8/40 N=4 pairs. None of the 80 all-shuffled controls produced either
target answer.

The independent observable-trace audit reviewed all successes and every
automatic stride classification. Among 90 signal successes, 58 were observable
one-pass tool-free responses and 23 contained concrete fixed-stride recognition
or testing. Those categories describe emitted events only; they do not expose
private reasoning or establish a transformer-only mechanism.

Full tables, Wilson intervals, effort analysis, qualitative findings, and the
interpretation boundary are in `results/analysis.md`. Raw subject stdout JSONL,
stderr, completed records, scoring decisions, audit decisions, prompt geometry,
and figures are all preserved separately.

## Cost-truncated tool-less pilot

The frozen pilot produced the expected ordered answer in 35/40 N=2 signal
trials. Both members of an equal-word-bag A/B pair were correct in 16/20 seeds.
The exact same prompts produced 29/40 signal successes and 11/20 discriminating
pairs under Codex. Both regimes were 40/40 on clean tasks. Neither produced a
target A or B answer on the 14 matched all-shuffled controls.

This establishes that Codex shell/filesystem tools and an agentic command loop
are not required for the observed N=2 ordered-lane behavior. It does not expose
private model reasoning or prove a unique internal mechanism. The nine
all-shuffled API nonresponses and five completed controls also show a major
effort increase without an intact stream.

See `results/raw-model-pilot-analysis.md` for the matched comparison,
scheduled- and completed-response analyses, effort measurements, cost caveat,
and interpretation boundary. `results/raw-model-pilot-freeze.json` records the
pre-scoring stopping rule, and `results/raw-model-pilot-audit.json` verifies
prompt matching, blind-review coverage, raw hashes, and scores.

## Reproduction and audit commands

Generate and mechanically validate the frozen prompt slate:

```bash
python3 -B experiment-2/generate.py
python3 -B experiment-2/validate.py
python3 -B experiment-2/simulate.py
```

The frozen Codex-agent invocation used the pinned image, four workers, and a
900-second subject timeout:

```bash
python3 -B experiment-2/run_codex.py \
  --root experiment-2 \
  --auth AUTH_JSON \
  --isolation-validation experiment-2/results/isolation-validation.json \
  --image sha256:883e4d8d659d28c25d2473c0dec9ff43d1bafb7ce3920ada270627df3c202402 \
  --workers 4 --timeout 900
```

Timeouts are protocol outcomes. Infrastructure failures are preserved and
rerun only after a mechanical audit. The nine quota-rejected first attempts are
under `invalidated-attempts/`, and their exact prompt hashes match the active
reruns.

Rebuild coordinator-side scoring and automatic analysis with:

```bash
python3 -B experiment-2/score.py
python3 -B experiment-2/trace_analysis.py
python3 -B experiment-2/analyze.py
python3 -B experiment-2/leakage_trace_audit.py
python3 -B experiment-2/audit.py --expected 320
```

The independent blind decisions in `results/blind-audit-decisions.jsonl` and
observable strategy decisions in `results/trace-strategy-audit.jsonl` are the
human-reviewed records. Regenerating automatic scores does not replace them.

Rebuild and audit the frozen tool-less pilot without making API calls:

```bash
python3 -B experiment-2/prepare_raw_pilot.py
python3 -B experiment-2/score.py \
  --input experiment-2/results/raw-model-pilot-unscored.jsonl \
  --output experiment-2/results/raw-model-pilot-auto-scored.jsonl \
  --audit-packet experiment-2/results/raw-model-pilot-blind-packet.jsonl
python3 -B experiment-2/apply_blind_audit.py \
  --root experiment-2 \
  --trials experiment-2/results/raw-model-pilot-auto-scored.jsonl \
  --decisions experiment-2/results/raw-model-pilot-blind-decisions.jsonl \
  --output experiment-2/results/raw-model-pilot-trials.jsonl
python3 -B experiment-2/analyze_raw_pilot.py
python3 -B experiment-2/audit_raw_model.py
python3 -B experiment-2/audit_raw_pilot.py
```

## Limitations and next step

The result establishes behavioral sensitivity to hidden word order while the
word bag is held constant. It does not by itself distinguish transformer-level
source separation from unobserved or explicit agentic decoding. Same-host
Docker is an audited practical isolation boundary, not cryptographic isolation.

The original 320-call tool-less slate should not be resumed: the 94-call pilot
already answers whether tools are required, and the remaining 226 calls have
poor information-per-dollar value. If a later follow-up is funded, use a small,
preregistered fixed-stride-versus-jittered-spacing paired test with a hard dollar
cap. That directly tests whether periodic position is the exploitable cue.
Larger N remains deferred.
