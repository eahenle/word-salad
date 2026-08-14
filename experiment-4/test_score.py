#!/usr/bin/env python3
from score_uniform import ANSWER_KEYS, extract_assignments

CASES = {
    "brass key = green; silver coin = blue; glass marble = green": ANSWER_KEYS["A"],
    "brass key: green\nsilver coin: red\nglass marble: green": ANSWER_KEYS["B"],
    "green = brass key and glass marble; blue = silver coin; red = empty": ANSWER_KEYS["A"],
    "red = silver coin; green = brass key and glass marble; blue = empty": ANSWER_KEYS["B"],
}
for text, expected in CASES.items():
    assert extract_assignments(text) == expected, (text, extract_assignments(text))
print(f"score tests passed: {len(CASES)}")
