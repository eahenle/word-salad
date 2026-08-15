# External replication protocol

## Preregistered question

When aggregate whitespace-word content is held constant, does the model's answer
track which ordered A/B payload is embedded in the stimulus?

## Configuration

Primary reference configuration:

- model: `gpt-5.6-sol`;
- reasoning: `medium` for Experiment 4A comparability;
- tools: none where the invocation surface permits;
- one fresh model invocation per prompt;
- no conversation reuse;
- timeout: 900 seconds;
- prompt bytes: unchanged from `frozen-prompts/`.

If the exact reference configuration is unavailable, record the actual model
and setting and call the result a cross-model replication, not an exact one.

## Isolation

The subject receives only the prompt body. Do not expose the repository,
manifests, filenames, condition, seed, answer keys, previous responses, or this
protocol to the subject. Disable tools, retrieval, browser, persistent memory,
and conversation history where possible. Record any capability that cannot be
disabled.

## Endpoints

Primary: complete paired discrimination within each study and seed:

```text
A prompt -> answer A
AND
B prompt -> answer B
```

Secondary: expected individual answer recovery. Control endpoint: either target
answer from an all-shuffled prompt. Preserve malformed and non-target responses.

Report exact numerator/denominator, percentage, and Wilson 95% confidence
interval. The experimental units are prompts under a fixed runtime, not sampled
models.

## Failure and retry policy

Timeouts after inference begins are outcomes and are not retried. A trial may be
rerun only after a documented pre-inference transport, authentication, or
capacity rejection that produced no model response. Preserve the rejected
attempt and rerun only that exact prompt.

## Freezing

Before inference, archive:

- Git commit and packet hashes;
- exact command and model configuration;
- timeout;
- runtime version;
- execution manifest;
- planned exclusions and retry rule.

Freeze all responses before scoring. Do not inspect responses to decide which
seeds or controls to retain.

## Interpretation

A successful replication supports behavioral sensitivity to embedded order
under the tested model/runtime. It does not establish a mechanism, arbitrary
subsequence recovery, practical exploitability, or universality across models.
