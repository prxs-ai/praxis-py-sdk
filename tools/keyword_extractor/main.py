#!/usr/bin/env python3
import os
import json
import re
from collections import Counter
from datetime import datetime


RU_STOP = {
    "и","в","во","не","что","он","на","я","с","со","как","а","то","все","она","так","его","но","да",
    "ты","к","у","же","вы","за","бы","по","только","ее","мне","было","вот","от","меня","еще","нет","о",
    "из","ему","теперь","когда","даже","ну","вдруг","ли","если","уже","или","ни","быть","был","него","до","вас",
    "нибудь","опять","уж","вам","ведь","там","потом","себя","ничего","ей","может","они","тут","где","есть","надо",
    "ней","для","мы","тебя","их","чем","была","сам","чтоб","без","будто","чего","раз","тоже","себе","под","будет",
}
EN_STOP = {
    "the","and","to","of","a","in","that","is","for","on","with","as","it","by","at","from","this","be","are",
    "was","or","an","we","you","they","he","she","but","not","have","has","had","will","can","about","into",
}


def tokenize(text: str):
    return [t.lower() for t in re.findall(r"[\w\-]+", text, flags=re.UNICODE)]


def extract_keywords(text: str, top_n: int = 5):
    tokens = tokenize(text)
    filtered = [t for t in tokens if t not in RU_STOP and t not in EN_STOP and len(t) > 2]
    freq = Counter(filtered)
    return freq.most_common(max(1, top_n))


def main():
    text = os.environ.get("text") or os.environ.get("TEXT") or ""
    try:
        top_n = int(os.environ.get("top_n") or os.environ.get("TOP_N") or 5)
    except Exception:
        top_n = 5

    if not text:
        print(json.dumps({
            "status": "error",
            "error": "No input text provided (env 'text')",
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }, ensure_ascii=False))
        return

    kw = extract_keywords(text, top_n)
    out = {
        "status": "success",
        "tool": "keyword_extractor",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "input": {
            "text_length": len(text),
            "top_n": top_n,
        },
        "keywords": [{"token": t, "count": c} for t, c in kw]
    }
    print(json.dumps(out, ensure_ascii=False))


if __name__ == "__main__":
    main()

