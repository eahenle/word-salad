# Literature-search questions

These questions should guide a primary-source literature review after Methods
and Results stabilize. They are deliberately phrased to test the manuscript's
framing rather than to retrofit citations to a mechanism.

## Corrupted and reordered language

1. How does human and model comprehension degrade under within-sentence word
   shuffling, local permutation, deletion, or insertion noise?
2. Which studies directly separate lexical bag information from word-order
   information in language-model behavior?
3. Are there established benchmarks for reconstructing coherent text from
   shuffled, interleaved, or multiplexed tokens?
4. What evidence distinguishes robust semantic inference from memorized lexical
   or task priors under corrupted input?

## Long-range order sensitivity

5. Which controlled studies test transformer sensitivity to nonadjacent ordered
   subsequences while holding token identity constant?
6. What primary work measures how attention heads represent relative position,
   induction patterns, or distant syntactic dependencies?
7. Do mechanistic studies show source-like separation of simultaneous sequences,
   and what evidence would be required before applying that language here?
8. How do positional encodings affect recovery when regular stride is removed?

## Noisy-channel and source-separation analogies

9. What is the closest formal noisy-channel literature for recovering intended
   linguistic structure under structured lexical interference?
10. Where has “source separation” been used behaviorally versus mechanistically
    in NLP, speech, vision-language, or sequence modeling?
11. What alternative terminology would avoid implying an established neural
    mechanism while accurately describing answer tracking from embedded order?

## Model capability and inference effort

12. What work separates capability gains from increased test-time computation
    or agentic search in reasoning models?
13. Are nonmonotonic reasoning-effort effects documented in controlled language
    evaluations?
14. Which trace-based studies distinguish direct responses from tool-assisted or
    iterative reconstruction without claiming access to private chain of thought?

## Robustness and peripheral security relevance

15. What primary prompt-injection research shows models following instructions
    embedded in untrusted content, and how is that different from this text-only
    answer-identity result?
16. Which defenses treat encoded or obfuscated instructions, and would citing
    them motivate future work without implying that this study demonstrates an
    exploit?
17. Are there benign robustness evaluations of hidden or indirect instruction
    processing with capability-free endpoints?

## Human baselines and evaluation design

18. What methods are standard for measuring human readability or decoding of
    corrupted/multiplexed text without revealing the manipulation?
19. How many raters and what preregistered endpoints would support a later human
    comparison on the exact frozen prompts?
20. What statistical framework best compares fixed model/runtime prompt trials
    without treating prompts or proprietary model families as random population
    samples?

## Search and inclusion discipline

- Prefer original papers, benchmark papers, and official technical reports.
- Record whether each source supports a behavioral observation, an evaluation
  method, or a mechanism; do not transfer claims across those categories.
- Search for disconfirming work and null results, not only adjacent successes.
- Keep prompt-injection citations peripheral unless the manuscript reports an
  actual instruction-following experiment, which the present core paper does
  not.
