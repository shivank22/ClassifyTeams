#!/usr/bin/env python3
"""Classify Teams threads via OpenAI Chat Completions API.

Usage:
  OPENAI_API_KEY=... python3 classify_threads.py \
    --input /path/to/anonymized_threads.json \
    --output /path/to/thread_classifications.json
"""
from __future__ import annotations

import argparse
import json
import os
import time
import urllib.request
import urllib.error
from typing import Any, Dict, List


def call_openai(base_url: str, api_key: str, model: str, messages: List[Dict[str, str]]) -> Dict[str, Any]:
    url = base_url.rstrip('/') + '/chat/completions'
    payload = {
        "model": model,
        "messages": messages,
        "response_format": {"type": "json_object"},
    }
    data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        body = resp.read().decode('utf-8')
    return json.loads(body)


def extract_json_content(resp: Dict[str, Any]) -> Dict[str, Any]:
    # Chat Completions response: choices[0].message.content should be JSON
    choices = resp.get("choices", [])
    if not choices:
        return {}
    message = choices[0].get("message", {})
    content = message.get("content", "")
    if not content:
        return {}
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        return {}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True, help="Path to anonymized_threads.json")
    ap.add_argument("--output", required=True, help="Where to write classification JSON")
    ap.add_argument("--base-url", default="https://api.openai.com/v1", help="OpenAI API base URL")
    ap.add_argument("--model", default="gpt-4.1-mini", help="Model name")
    ap.add_argument("--sleep", type=float, default=0.0, help="Seconds to sleep between requests")
    ap.add_argument("--max-retries", type=int, default=2, help="Retries per thread on API errors")
    args = ap.parse_args()

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise SystemExit("OPENAI_API_KEY env var is required")

    with open(args.input, "r", encoding="utf-8") as f:
        data = json.load(f)

    threads = data.get("threads", [])
    results = []

    system_prompt = (
        "You are a classifier. Return ONLY JSON. "
        "Extract these fields from the thread messages: "
        "Incident Number (e.g., INC123456 or empty string if unknown), "
        "Root Cause (short phrase), Type (Restart or Error), "
        "Severity (High, Med, Low)."
    )

    for idx, thread in enumerate(threads, start=1):
        thread_id = thread.get("thread_id")
        messages = thread.get("messages", [])

        user_payload = {
            "thread_id": thread_id,
            "messages": messages,
        }

        chat_messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": "JSON input:\n" + json.dumps(user_payload, ensure_ascii=False)},
        ]

        attempt = 0
        parsed: Dict[str, Any] = {}
        error: str | None = None
        while attempt <= args.max_retries:
            try:
                resp = call_openai(args.base_url, api_key, args.model, chat_messages)
                parsed = extract_json_content(resp)
                if parsed:
                    break
                error = "Empty or invalid JSON response"
            except (urllib.error.HTTPError, urllib.error.URLError, json.JSONDecodeError) as e:
                error = str(e)
            attempt += 1
            time.sleep(1.0)

        result = {
            "thread_id": thread_id,
            "incident_number": parsed.get("Incident Number", ""),
            "root_cause": parsed.get("Root Cause", ""),
            "type": parsed.get("Type", ""),
            "severity": parsed.get("Severity", ""),
            "error": error if not parsed else None,
        }
        results.append(result)

        # Write partial results so progress is saved
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump({"results": results}, f, ensure_ascii=False, indent=2)

        if args.sleep:
            time.sleep(args.sleep)

        print(f"Processed {idx}/{len(threads)}: {thread_id}")

    print(f"Wrote {len(results)} classifications to {args.output}")


if __name__ == "__main__":
    main()
