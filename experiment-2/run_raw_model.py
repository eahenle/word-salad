#!/usr/bin/env python3
"""Run exact tool-less GPT-5.6-Sol-xhigh subjects through the Responses API.

This runner deliberately refuses to start without a normal OpenAI API key. It
does not reuse Codex session credentials and never substitutes another model.
"""

from __future__ import annotations

import argparse
import json
import os
import ssl
import urllib.error
import urllib.request
from pathlib import Path


def load_project_api_key(path: Path) -> str | None:
    """Load only OPENAI_API_KEY from a git-ignored project env file."""
    key = os.environ.get("OPENAI_API_KEY")
    if key:
        return key
    if not path.is_file():
        return None
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, value = line.split("=", 1)
        if name.strip() != "OPENAI_API_KEY":
            continue
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        return value or None
    return None


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prompt", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--model", default="gpt-5.6-sol")
    parser.add_argument("--reasoning", default="xhigh")
    parser.add_argument("--timeout", type=float, default=900)
    parser.add_argument(
        "--ca-file",
        type=Path,
        help="additional public CA certificate for verified HTTPS (for inspected networks)",
    )
    parser.add_argument(
        "--env-file",
        type=Path,
        default=Path(__file__).resolve().parent.parent / ".env",
    )
    args = parser.parse_args()
    if args.model != "gpt-5.6-sol" or args.reasoning != "xhigh":
        raise SystemExit("this experimental runner permits only exact gpt-5.6-sol/xhigh")
    key = load_project_api_key(args.env_file)
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
    context = ssl.create_default_context()
    if args.ca_file:
        context.load_verify_locations(cafile=args.ca_file)
    try:
        with urllib.request.urlopen(request, timeout=args.timeout, context=context) as response:
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
