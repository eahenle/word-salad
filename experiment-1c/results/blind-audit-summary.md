# Blind audit summary

## Scope and coverage

- Audited all 320 records in `blind-audit-packet.jsonl`, keyed only by `audit_id`.
- Used the expected assignments: brass key = red, silver coin = blue, glass marble = blue.
- Reviewed the packet in 20-record streaming batches. Mechanically checked exact strings, all three assignment relations, the six possible material/noun object substitutions, and encoding vocabulary. Manually inspected every non-success, ambiguous response, malformed-object response, parser miss, encoding-positive response, nonresponse, and `other` classification.
- No condition, variant, lane, phase, seed, or neutral identifier was available or used. The source packet and trial data were not modified.

## Reviewed outcome totals

| Reviewed classification | Count |
|---|---:|
| encoding_discovery_without_task_completion | 93 |
| exact_task_success | 13 |
| nonresponse | 1 |
| other | 8 |
| partial_recovery | 136 |
| semantic_task_success | 69 |

Reviewed full task success is 82/320: 13 exact-format successes and 69 additional semantic successes.

## Automatic-versus-reviewed discrepancies

| Field | Discrepant records | Audit IDs |
|---|---:|---|
| exact_success | 0 | none |
| semantic_success | 1 | 15254dd3b77a |
| correct_assignment_count | 11 | 0205269be903, 15254dd3b77a, 4bcdc5f4805f, 75bb8147b7d9, 99fd4c3b023a, c283878bcf38, d5bc717aa2b8, db97792db003, e0b4db773239, ef0fdc10fb14, fc28a03ae7cf |
| malformed_object_substitutions | 0 | none |
| encoding_discovered | 1 | e0b4db773239 |
| classification | 60 | 60 records; see transition counts below and per-record notes in the decisions file |

Classification transitions:

- partial_recovery -> encoding_discovery_without_task_completion: 59
- partial_recovery -> semantic_task_success: 1

The assignment-count overrides consist of two automatic false positives from explicitly hypothetical/starting states and nine parser misses involving unique-object abbreviations or clear box-content syntax. The sole semantic-success override is `15254dd3b77a`. Malformed substitution detection was complete for all six invalid material/noun combinations. Encoding detection missed `e0b4db773239`, whose response explicitly identified duplicated, contradictory moves.

The largest classification discrepancy is systematic: encoding-positive responses that recognized the text manipulation but stopped without a final task answer were inconsistently split between `partial_recovery` and `encoding_discovery_without_task_completion`. Reviewed classifications apply the named category consistently. `230c6ac19484` remains `partial_recovery` because it recognizes the scrambling and also supplies a concrete, incorrect final mapping.
