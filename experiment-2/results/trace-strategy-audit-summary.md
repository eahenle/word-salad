# Experiment 2 observable trace-strategy audit

## Coverage and selection

- Audited 269 unique trials from the immutable trial, trace-metric, and raw-trace files.
- Mandatory coverage: all 170 trials with `semantic_success: true` and all 108 trials automatically classified as `explicit_fixed_stride_hypothesis` or `explicit_testing_of_candidate_strides` (overlap was deduplicated).
- Supplemental coverage: 28 failures/controls outside those mandatory strata, exceeding the requested minimum of 20. The sample deliberately spans both arms, signal and all-shuffled controls, two- and four-lane prompts, and direct, lexical, recognition-only, and tool-assisted automatic categories.

Audited neutral IDs (269): r0001, r0002, r0003, r0004, r0005, r0006, r0007, r0008, r0009, r0010, r0011, r0012, r0013, r0014, r0015, r0016, r0017, r0018, r0019, r0020, r0021, r0022, r0023, r0024, r0025, r0026, r0027, r0028, r0029, r0030, r0031, r0032, r0033, r0034, r0035, r0036, r0037, r0038, r0039, r0040, r0041, r0042, r0043, r0044, r0045, r0046, r0048, r0050, r0052, r0053, r0054, r0055, r0056, r0057, r0058, r0059, r0060, r0061, r0062, r0064, r0066, r0067, r0070, r0071, r0072, r0073, r0074, r0076, r0077, r0079, r0080, r0081, r0082, r0084, r0085, r0087, r0088, r0090, r0092, r0095, r0096, r0098, r0100, r0101, r0102, r0103, r0104, r0105, r0106, r0107, r0110, r0111, r0112, r0113, r0114, r0115, r0117, r0118, r0119, r0120, r0121, r0122, r0123, r0124, r0125, r0128, r0129, r0130, r0131, r0132, r0133, r0134, r0135, r0136, r0137, r0138, r0139, r0140, r0141, r0142, r0144, r0145, r0146, r0148, r0149, r0152, r0153, r0154, r0155, r0156, r0158, r0159, r0160, r0161, r0162, r0163, r0164, r0165, r0166, r0167, r0168, r0169, r0170, r0171, r0172, r0173, r0174, r0175, r0176, r0177, r0178, r0179, r0180, r0181, r0182, r0183, r0184, r0185, r0186, r0187, r0188, r0189, r0190, r0191, r0192, r0193, r0194, r0195, r0196, r0197, r0198, r0199, r0200, r0201, r0202, r0203, r0204, r0205, r0206, r0207, r0209, r0211, r0212, r0213, r0215, r0216, r0217, r0218, r0219, r0220, r0221, r0223, r0224, r0226, r0227, r0228, r0229, r0230, r0233, r0234, r0235, r0236, r0238, r0240, r0241, r0242, r0243, r0244, r0245, r0247, r0248, r0249, r0250, r0251, r0253, r0255, r0257, r0258, r0259, r0260, r0261, r0262, r0263, r0264, r0265, r0267, r0268, r0269, r0270, r0271, r0272, r0273, r0275, r0277, r0278, r0279, r0280, r0282, r0283, r0284, r0286, r0287, r0288, r0289, r0290, r0291, r0292, r0295, r0296, r0297, r0298, r0299, r0300, r0301, r0303, r0304, r0305, r0306, r0307, r0308, r0309, r0310, r0311, r0312, r0313, r0316, r0317, r0319, r0320.

Supplemental sample by design stratum:

- constrained / all_shuffled / 2 lanes: 2
- constrained / all_shuffled / 4 lanes: 4
- constrained / signal / 2 lanes: 2
- constrained / signal / 4 lanes: 5
- explanation / all_shuffled / 2 lanes: 4
- explanation / all_shuffled / 4 lanes: 4
- explanation / signal / 2 lanes: 3
- explanation / signal / 4 lanes: 4

## Review rule

This is an audit of observable trace behavior only. No claim is made about private reasoning. A fixed-stride classification required concrete trace evidence: every-nth-word/residue extraction, explicit every-nth recognition, or testing fixed stride values. Generic words such as “interleaved,” “repeated,” or “shuffled” were not enough. Multi-command non-stride work was classified as repeated reconstruction; relevant one- or two-tool lexical work without stride was classified as tool-assisted lexical reconstruction; completed one-turn responses without tools were classified as direct; and traces without an observable specified mechanism were indeterminate.

## Reviewed strategies

| Reviewed strategy | Count |
|---|---:|
| direct_one_pass_tool_free_response | 152 |
| explicit_fixed_stride_recognition_or_testing | 42 |
| indeterminate | 14 |
| repeated_reconstruction | 49 |
| shell_or_tool_assisted_lexical_reconstruction_without_stride | 12 |

Automatic categories in the audited subset:

- apparent_lexical_reconstruction: 5
- direct_one_pass_response: 137
- explicit_fixed_stride_hypothesis: 94
- explicit_recognition_of_shuffled_text: 5
- explicit_testing_of_candidate_strides: 14
- shell_or_tool_assisted_reconstruction: 14

## Confirmations and corrections

- Reviewed strategy agreed with the normalized automatic category for 201/269 audited trials; 68 were corrected.
- Of 108 automatic explicit-stride trials, 42 had observable fixed-stride evidence and 66 did not.
- Of 14 automatic candidate-stride trials, 12 actually compared candidate fixed strides. The automatic scorer missed candidate-stride testing in 3 other trials: r0154, r0257, r0319.
- The two automatic candidate-stride false positives were `r0122` (offsets within one fixed stride) and `r0295` (general order-preserving interleaving/permutation search).

Flag discrepancies:

- `direct_one_pass` versus reviewed direct/tool-free: 2 (r0112, r0263).
- `fixed_stride_hypothesis`: 66 (r0084, r0088, r0092, r0095, r0101, r0102, r0104, r0107, r0110, r0112, r0113, r0114, r0115, r0118, r0123, r0125, r0129, r0130, r0134, r0135, r0137, r0140, r0142, r0146, r0148, r0152, r0153, r0155, r0158, r0160, r0213, r0241, r0245, r0253, r0260, r0262, r0263, r0264, r0265, r0271, r0272, r0277, r0278, r0282, r0283, r0286, r0287, r0289, r0290, r0291, r0292, r0295, r0296, r0298, r0299, r0300, r0303, r0304, r0305, r0307, r0308, r0310, r0312, r0316, r0317, r0320).
- `candidate_stride_testing`: 5 (r0122, r0154, r0257, r0295, r0319).
- `shell_or_tool_assisted`: 0 (none).
- `repeated_reanalysis` versus reviewed repeated reconstruction: 0 (none).
- `lexical_reconstruction_without_stride` and `indeterminate` are reviewed semantic flags with no one-to-one automatic counterpart, so no artificial discrepancy count is reported for them.

Correction transitions after mapping automatic categories onto the five reviewed categories:

- explicit_fixed_stride_recognition_or_testing -> direct_one_pass_tool_free_response: 11
- explicit_fixed_stride_recognition_or_testing -> indeterminate: 8
- explicit_fixed_stride_recognition_or_testing -> repeated_reconstruction: 41
- explicit_fixed_stride_recognition_or_testing -> shell_or_tool_assisted_lexical_reconstruction_without_stride: 6
- indeterminate -> direct_one_pass_tool_free_response: 2

## Limitations

- The audit classifies recorded agent messages and recorded tool activity; it cannot observe or infer hidden chain-of-thought.
- A tool-free answer may have involved internal processing, but is labeled direct here because the observable trace contains no tool-assisted reconstruction.
- Some traces end after a progress message or contain failed/irrelevant tool probes. These are marked indeterminate unless another specified strategy is directly observable.
- The supplemental failure/control set is stratified but not a random probability sample, so its correction rate should not be generalized to all unaudited failures.
- Source trials, automatic metrics, and raw traces were not modified.
