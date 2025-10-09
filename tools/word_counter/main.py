#!/usr/bin/env python3

import json
import os
import sys
from pathlib import Path


def count_words(file_path: str) -> dict:
    try:
        path = Path(file_path)
        if not path.exists():
            return {"success": False, "error": f"File not found: {file_path}"}

        with open(path, encoding="utf-8") as f:
            content = f.read()

        lines = content.split("\n")
        words = content.split()
        characters = len(content)
        characters_no_spaces = len(content.replace(" ", ""))

        return {
            "success": True,
            "file": str(path),
            "counts": {
                "words": len(words),
                "lines": len(lines),
                "characters": characters,
                "characters_no_spaces": characters_no_spaces,
                "unique_words": len(
                    set(word.lower().strip('.,!?;:"()[]{}') for word in words)
                ),
            },
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def main():
    file_path = os.environ.get("FILE_PATH") or os.environ.get("file_path")

    if not file_path:
        if len(sys.argv) > 1:
            file_path = sys.argv[1]
        else:
            result = {
                "success": False,
                "error": "FILE_PATH environment variable or command line argument required",
            }
            print(json.dumps(result, indent=2))
            sys.exit(1)

    result = count_words(file_path)
    print(json.dumps(result, indent=2))

    if not result.get("success", False):
        sys.exit(1)


if __name__ == "__main__":
    main()
