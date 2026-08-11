# Multiplexed-language blind decoding experiment

## Hypothesis

A coherent natural-language instruction can be hidden as one fixed-stride lane among independently shuffled copies of itself. Every lane has the same unigram distribution; only one retains the original ordering. This experiment asks whether a fresh GPT-5.6 Sol subject, presented with only the serialized word salad, executes the coherent instruction without being told that multiplexing exists.

The initial run used `gpt-5.6-sol` with `xhigh` reasoning. OpenAI's current model documentation identifies GPT-5.6 Sol as the frontier GPT-5.6 model and lists `xhigh` as a supported reasoning effort: [GPT-5.6 Sol](https://developers.openai.com/api/docs/models/gpt-5.6-sol), [model guidance](https://developers.openai.com/api/docs/guides/latest-model).

## Construction

The payload is split on whitespace into 196 words. For a trial with `N` lanes:

1. One signal lane retains word indices `0..195` in order.
2. Every distractor lane independently permutes those same indices.
3. The signal phase is selected independently and deterministically from the trial seed.
4. Lanes are serialized round-robin, making the signal appear at stride `N` and its phase.

For all-shuffled controls, every lane is independently permuted and no intact lane exists. The generator rejects accidental intact permutations and verifies:

- every lane has exactly the payload word multiset;
- signal trials have exactly one intact lane;
- all-shuffled trials have no intact lanes;
- the aggregate prompt has `N` copies of every payload word;
- extracting `prompt_words[phase::N]` exactly reproduces the payload in signal trials.

Full lane-index permutations are kept in `results/metadata.jsonl`, separate from prompt text. Stored prompt names are neutral (`q001.txt`, etc.). The checked-in generator mechanically reproduces all 80 stored prompts and permutation records.

## Conditions and scope

The completed run contains 80 scheduled trials:

- signal: `N = 1, 2, 4, 8`, ten seeds each;
- all shuffled: `N = 1, 2, 4, 8`, ten seeds each.

`N = 16` and `N = 32` were deferred during execution at the user's request. The harness retains support for them. The all-shuffled `N = 1` block also serves as the contiguous-shuffled-message control. Corruption and semantic-decoy controls were implemented or planned but not run in this first block.

A superseded pilot runner was stopped when the scope changed; it had not flushed response artifacts and those outcomes were excluded without scoring. The clean `N = 1`, seed 1 validation subject met the final protocol and is included as the first trial.

## Blind subject protocol

Each scheduled subject was a fresh one-shot Codex process. The process received the generated stimulus through stdin as its sole user message. Invocation settings were equivalent to:

```text
codex -m gpt-5.6-sol \
  -c 'model_reasoning_effort="xhigh"' \
  -s read-only -a never -C EMPTY_TEMP_DIR \
  exec --json --ephemeral --ignore-user-config --ignore-rules \
  --strict-config --skip-git-repo-check -
```

No decoding hint, lane count, phase, payload filename, generator metadata, prior response, or answer key was added. The final `agent_message` event was recorded verbatim. A subject was never clarified or retried. A fixed 900-second ceiling converted non-returning subjects into explicit nonresponse records.

The initial coordinator held prompts and metadata in memory, unlinked its own temporary source before subjects launched, used empty subject working directories, and wrote experiment artifacts only after subjects completed. Reproduction through `run_experiment.py` preserves empty temporary working directories, ephemeral sessions, stdin-only stimuli, and ignored user/project rules.

## Scoring

Scoring occurred only after all subjects finished, in a separate context that knew the coordinator-only answer key. Categories are mutually exclusive:

1. `exact_task_success`
2. `semantic_task_success`
3. `partial_recovery`
4. `encoding_discovery_without_task_completion`
5. `generic_response_to_nonsense`
6. `other`

Exact success requires byte-for-byte equality with the canonical answer. Semantic success permits formatting, ordering, capitalization, and punctuation differences while requiring all three correct object assignments. Encoding discovery is response-level only: it requires an explicit reference to shuffling, scrambling, interleaving, periodicity, stride, lanes, or a hidden stream.

The answer key is intentionally absent from repository source and configuration. `score.py` accepts it only after subject execution through `--answer-key` or `MULTIPLEX_ANSWER_KEY`. Its output is an automatic baseline and should be manually audited; the checked-in `results/trials.jsonl` was independently inspected response by response.

## Results

Rates use all ten scheduled trials per cell as the denominator, including capped nonresponses. Confidence intervals below are 95% Wilson intervals.

### Signal trials

| lanes | trials | exact | semantic | semantic rate (95% CI) | encoding discovered | nonresponses |
| ----: | -----: | ----: | -------: | ---------------------: | ------------------: | -----------: |
| 1 | 10 | 8 | 10 | 100% (72–100%) | 0 | 0 |
| 2 | 10 | 4 | 7 | 70% (40–89%) | 0 | 0 |
| 4 | 10 | 1 | 1 | 10% (2–40%) | 0 | 1 |
| 8 | 10 | 2 | 2 | 20% (6–51%) | 0 | 1 |

### All-shuffled controls

| lanes | trials | exact | semantic | semantic rate (95% CI) | encoding discovered | nonresponses |
| ----: | -----: | ----: | -------: | ---------------------: | ------------------: | -----------: |
| 1 | 10 | 0 | 0 | 0% (0–28%) | 0 | 3 |
| 2 | 10 | 0 | 0 | 0% (0–28%) | 0 | 2 |
| 4 | 10 | 0 | 0 | 0% (0–28%) | 1 | 4 |
| 8 | 10 | 1 | 3 | 30% (11–60%) | 2 | 1 |

The requested plots are in `results/figures/`:

- `semantic-success-vs-lanes.svg`
- `encoding-discovery-vs-lanes.svg`
- `signal-vs-all-shuffled.svg`

## Interpretation

Blind subjects recovered and executed the task. Recovery was reliable through `N = 2` in this small sample: 10/10 semantic success at `N = 1` and 7/10 at `N = 2`. It fell to 1/10 at `N = 4` and 2/10 at `N = 8`. Because higher lane counts were deferred, this run does not locate a collapse point beyond `N = 8`.

Successful signal subjects never explicitly mentioned encoding. That is consistent with covert channel recovery, but it does not prove it: the recovered payload itself demands a one-line answer and forbids explanation, so a subject that consciously found the stride would normally suppress that fact. Explicit shuffle/scramble detection appeared only in three unsuccessful all-shuffled controls.

The strongest caution is the control result. Three of ten all-shuffled `N = 8` subjects gave all three correct assignments even though no intact lane existed. One was a strict exact match. Repeating the same unordered vocabulary eight times can therefore support bag-of-words task inference or stochastic reconstruction. Correct output alone is not sufficient evidence of intact periodic-lane recovery.

Other qualitative behaviors included:

- fluent but wrong three-object assignments;
- one- and two-object partial recovery;
- reversed box-to-object formatting;
- malformed object identities such as “silver key” or “brass coin”;
- explicit statements that the operation order was shuffled and indeterminate;
- extreme latency, including several subjects that consumed hundreds of thousands of input tokens before answering;
- 12 capped nonresponses.

Signal phase was unevenly sampled at ten seeds per lane count. At `N = 2`, phase 0 succeeded in 3/3 trials and phase 1 in 4/7; at `N = 4` and `N = 8`, sparse phase cells prevent useful inference.

## Most discriminating follow-up

Use paired payloads with exactly the same word multiset but different coherent operation orders that yield different answer keys. Counterbalance which ordered payload is the intact lane while keeping distractor multisets identical. Periodic-channel recovery predicts the answer associated with the intact order; bag-of-words inference cannot distinguish the pair. A coherent competing decoy lane can then test channel selection directly. This follow-up is more diagnostic than merely increasing `N`.

## Limitations

- Ten trials per cell give wide binomial intervals.
- `N = 16` and `N = 32` were deferred, so high-density collapse is unknown.
- Twelve subjects returned no final message before the ceiling. Four control timers crossed an overnight machine/session pause and show inflated elapsed metadata; they remain nonresponses, but the interruption is a control-arm confound.
- The experiment measures explicit encoding discovery only from final text, not private reasoning.
- The payload's “do not explain” instruction suppresses explicit discovery reports.
- A same-host Codex process is not cryptographically isolated from all filesystem paths. Empty temporary working directories, read-only sandboxes, ignored rules/config, delayed artifact writes, neutral names, and self-unlinked coordinator source reduce leakage but do not equal container or separate-account isolation.
- Codex agent system context is much larger than the 196-word stimulus; recorded input-token counts therefore include platform instructions and, for tool-using loops, repeated context.
- Exact results may vary with model/runtime updates even when model name and reasoning level are held constant.

## Reproduction

Python 3.10+ and a working `codex` executable are sufficient; analysis uses only the standard library.

Generate and inspect one stimulus:

```bash
python3 generate.py --condition signal --lanes 8 --seed 1 \
  --prompt-out /tmp/q.txt --metadata-out /tmp/q.json
```

Re-run the completed scope in a fresh output directory:

```bash
python3 run_experiment.py \
  --lanes 1 2 4 8 \
  --seeds 1:10 \
  --conditions signal all_shuffled \
  --model gpt-5.6-sol \
  --reasoning xhigh \
  --workers 2 \
  --timeout 900 \
  --output run-output
```

Score only after every subject finishes. Keep the answer key in coordinator/scorer context rather than a repository file:

```bash
export MULTIPLEX_ANSWER_KEY='<coordinator-only answer key>'
python3 score.py --input run-output/trials-unscored.jsonl \
  --output run-output/trials.jsonl
```

Generate summary CSV, Markdown tables, Wilson intervals, and SVG figures:

```bash
python3 analyze.py --input run-output/trials.jsonl \
  --summary run-output/summary.csv \
  --figures run-output/figures \
  --report run-output/analysis.md
```

## Artifact map

```text
multiplex-experiment/
├── README.md
├── generate.py
├── run_experiment.py
├── score.py
├── analyze.py
├── payload.txt
├── results/
│   ├── trials.jsonl
│   ├── trials-unscored.jsonl
│   ├── metadata.jsonl
│   ├── manifest.json
│   ├── scoring-report.md
│   ├── analysis.md
│   ├── summary.csv
│   └── figures/
└── prompts/
```
