
#!/usr/bin/env python3
"""Build thread->messages JSON from a Teams export, anonymizing user names.

Usage:
  python3 anonymize_messages.py \
    --input /path/to/messages.json \
    --output /path/to/anonymized_threads.json
"""
from __future__ import annotations

import argparse
import html
import json
import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

TAG_RE = re.compile(r"<[^>]+>")


def strip_html(content: str) -> str:
    # Minimal HTML to text for Teams body.content
    text = TAG_RE.sub("", content)
    text = html.unescape(text)
    return " ".join(text.split())


def parse_iso(dt: Optional[str]) -> Tuple[int, str]:
    if not dt:
        return (0, "")
    try:
        return (int(datetime.fromisoformat(dt.replace("Z", "+00:00")).timestamp()), dt)
    except ValueError:
        return (0, dt)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True, help="Path to Teams messages.json")
    ap.add_argument("--output", required=True, help="Path to write anonymized threads JSON")
    ap.add_argument("--keep-html", action="store_true", help="Keep raw HTML content instead of stripping tags")
    args = ap.parse_args()

    with open(args.input, "r", encoding="utf-8") as f:
        data = json.load(f)

    messages: List[Dict[str, Any]] = data.get("messages", [])

    # Map message id -> message for lookup
    by_id: Dict[str, Dict[str, Any]] = {}
    for m in messages:
        mid = m.get("id")
        if isinstance(mid, str):
            by_id[mid] = m

    threads: Dict[str, List[Dict[str, Any]]] = {}

    for m in messages:
        # Group by conversationIdentity.conversationId (Teams thread id)
        conv = m.get("conversationIdentity", {}) if isinstance(m.get("conversationIdentity"), dict) else {}
        conv_id = conv.get("conversationId")
        if not conv_id:
            continue
        threads.setdefault(conv_id, [])

        body = m.get("body", {}) if isinstance(m.get("body"), dict) else {}
        content = body.get("content") if isinstance(body, dict) else ""
        if content is None:
            content = ""

        msg = {
            "user": {"displayName": "XXXX"},
            "message": content if args.keep_html else strip_html(str(content)),
            "_sort": m.get("createdDateTime"),
        }
        threads[conv_id].append(msg)

    # Sort messages in each thread by createdDateTime
    thread_list = []
    for tid, msgs in threads.items():
        msgs.sort(key=lambda x: parse_iso(x.get("_sort")))
        thread_sort = msgs[0].get("_sort") if msgs else None
        thread_list.append({"thread_id": tid, "messages": msgs, "_thread_sort": thread_sort})

    # Sort threads by first message time
    thread_list.sort(key=lambda t: parse_iso(t.get("_thread_sort")) if t["messages"] else (0, ""))
    for t in thread_list:
        for msg in t["messages"]:
            msg.pop("_sort", None)
        t.pop("_thread_sort", None)

    out = {"threads": thread_list}
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

    print(f"Wrote {len(thread_list)} threads to {args.output}")


if __name__ == "__main__":
    main()
