#!/usr/bin/env python3
import os
import json
import re
from datetime import datetime


def split_sentences(text: str):
    # Simple sentence splitter by punctuation
    parts = re.split(r"(?<=[\.!?])\s+", text.strip())
    return [p.strip() for p in parts if p.strip()]


def summarize(text: str, max_sentences: int = 2):
    sentences = split_sentences(text)
    if not sentences:
        return ""
    return " ".join(sentences[: max(1, max_sentences)])


def main():
    text = os.environ.get("text") or os.environ.get("TEXT") or ""
    try:
        sentences = int(os.environ.get("sentences") or os.environ.get("SENTENCES") or 2)
    except Exception:
        sentences = 2

    if not text:
        result = {
            "status": "error",
            "error": "No input text provided (env 'text')",
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }
        print(json.dumps(result, ensure_ascii=False))
        return

    summary = summarize(text, sentences)
    words = re.findall(r"\w+", text, flags=re.UNICODE)
    out = {
        "status": "success",
        "tool": "text_summarizer",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "input": {
            "text_length": len(text),
            "words": len(words),
            "sentences_requested": sentences,
        },
        "summary": summary,
        "summary_sentences": split_sentences(summary),
    }
    print(json.dumps(out, ensure_ascii=False))


if __name__ == "__main__":
    main()

