# Blind audit summary

- Input packet records processed: 320
- Decision records written: 320
- Unique IDs checked: 320 (packet) / 320 (decisions), exact match: yes

## Class mapping and override counts

| Source classification (raw) | Count |
| --- | ---: |
| answer_a | 3 |
| encoding_discovery_without_answer | 26 |
| expected_answer_success | 170 |
| indeterminate_or_refusal | 90 |
| other_assignment | 31 |

| Source classification (mapped for review comparison) | Count |
| --- | ---: |
| answer_a | 91 |
| answer_b | 82 |
| indeterminate_or_refusal | 90 |
| other_assignment | 31 |
| encoding_discovery_without_answer | 26 |

| Reviewed classification | Count |
| --- | ---: |
| answer_a | 91 |
| indeterminate_or_refusal | 91 |
| answer_b | 82 |
| other_assignment | 31 |
| encoding_discovery_without_answer | 25 |

- Overrides against mapped source class: 4
- `2d1ba63bf5bc`: raw=`encoding_discovery_without_answer` mapped->`encoding_discovery_without_answer`, reviewed=`indeterminate_or_refusal`
- `5409291eca3d`: raw=`encoding_discovery_without_answer` mapped->`encoding_discovery_without_answer`, reviewed=`indeterminate_or_refusal`
- `6031535fabf0`: raw=`other_assignment` mapped->`other_assignment`, reviewed=`encoding_discovery_without_answer`
- `bc27c57286d0`: raw=`indeterminate_or_refusal` mapped->`indeterminate_or_refusal`, reviewed=`other_assignment`

## Reviewed-field overrides

- `reviewed_indeterminate_claimed` changed in 2 records: 2d1ba63bf5bc, 5409291eca3d
- `reviewed_encoding_discovered_in_final` changed in 18 records: 03dae5b9bca3, 1d598d321f9e, 265d6ab9c2fd, 308906b3ff07, 4311a7ddcf32, 4cc09287b688, 4f22eea83a27, 50ff0706a51a, 5f18aa6541f3, 6031535fabf0, 6238fe4eddc2, 8a1a8f3c94eb, 90dec6263c5c, 93f2f8e8cb5b, 980a1837d279, 9c565ec75464, e76c55c6d37b, f0faa561ac8c
- Identity pass-through fields changed in 0 records
- Full reviewed assignments recorded in 197 records; `24` of those had both identity fields null (null preserved by instruction when packet identity absent).

## Recurring ambiguities

- 24 records have full object assignments in packet responses but no packet identity fields; reviewed identity fields were intentionally left null in all corresponding reviewed lines.
- 123 records have `reviewed_assignments: null`.
- 67 records were marked `reviewed_indeterminate_claimed: true`, including 2 where the source flag was false and 65 where the source flag was true.
