#!/usr/bin/env python3
"""Run exact tool-less GPT-5.6-Sol-xhigh subjects through the Responses API.

This runner deliberately refuses to start without a normal OpenAI API key. It
does not reuse Codex session credentials and never substitutes another model.
"""

from __future__ import annotations

import argparse
import json
import os
import urllib.error
import urllib.request
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prompt", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--model", default="gpt-5.6-sol")
    parser.add_argument("--reasoning", default="xhigh")
    parser.add_argument("--timeout", type=float, default=900)
    args = parser.parse_args()
    if args.model != "gpt-5.6-sol" or args.reasoning != "xhigh":
        raise SystemExit("this experimental runner permits only exact gpt-5.6-sol/xhigh")
    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        status = {
            "available": False,
            "reason": "OPENAI_API_KEY is not configured",
            "model": args.model,
            "reasoning_effort": args.reasoning,
            "substitution_performed": False,
        }
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(status, indent=2) + "\n")
        raise SystemExit("exact tool-less invocation unavailable: OPENAI_API_KEY is not configured")
    body = json.dumps({
        "model": args.model,
        "input": args.prompt.read_text(encoding="utf-8"),
        "reasoning": {"effort": args.reasoning},
        "tools": [],
        "store": False,
    }).encode()
    request = urllib.request.Request(
        "https://api.openai.com/v1/responses",
        data=body,
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=args.timeout) as response:
            raw = response.read()
    except urllib.error.HTTPError as exc:
        raw = exc.read()
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_bytes(raw)
        raise SystemExit(f"Responses API returned HTTP {exc.code}; raw response preserved")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(raw)
    print(f"wrote exact tool-less raw response to {args.output}")


if __name__ == "__main__":
    main()
