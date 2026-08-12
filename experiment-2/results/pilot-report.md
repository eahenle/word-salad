# Experiment 2 paired-order pilot

The preregistered seed-1 pilot completed all ten requested Codex-agent trials:
clean A/B, signal A/B at N=2, and an all-shuffled control, in both constrained
and explanation-permitted arms. All runner exits were normal and the artifact
integrity audit passed.

## Behavioral result

| arm | condition | A stimulus → A answer | B stimulus → B answer | all-shuffled A/B answer |
| --- | --- | ---: | ---: | ---: |
| constrained | clean | 1/1 | 1/1 | — |
| constrained | signal N=2 | 1/1 | 1/1 | — |
| constrained | all shuffled N=2 | — | — | 0/1 |
| explanation permitted | clean | 1/1 | 1/1 | — |
| explanation permitted | signal N=2 | 1/1 | 1/1 | — |
| explanation permitted | all shuffled N=2 | — | — | 0/1 |

Thus, in this small pilot, changing only the ordered signal lane changed the
answer in the predicted direction in 4/4 signal or clean A/B contrasts. Both
all-shuffled subjects refused to claim a unique result.

## Observable strategy

Seven of the eight clean/signal successes, including three of four multiplexed
signal trials, emitted no tools and completed in one turn. The remaining signal
success explicitly separated the two modulo-2 streams with one shell call.
Neither explanation-permitted signal final response spontaneously mentioned
interleaving, although absence from the final response is not evidence that the
model lacked such a hypothesis.

Both all-shuffled controls behaved very differently: they used 12 and 13 tool
calls, consumed 407,652 and 336,851 input tokens, and took 638 and 489 seconds
before declining to choose. This pilot therefore distinguishes inexpensive
tool-free successes, one explicit agentic decode, and expensive unordered
reconstruction failures.

## Isolation and decision

The pinned hardened-container validation passed before execution. Full raw
stdout JSONL, stderr, hashes, exit state, elapsed time, thread ID, and aggregate
usage were preserved per trial. The post-hoc leakage audit found no observed
host/repository or experiment-context access. Same-host Docker isolation is an
audited practical boundary, not cryptographic isolation.

The pilot found no methodological failure. The protocol is frozen unchanged
for the full 20-seed N=2/N=4 Codex-agent slate.
