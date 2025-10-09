#!/usr/bin/env python3
"""Text Analyzer Tool for Praxis
Analyzes text files and counts letters (Russian and English)
"""

import json
import os
import sys
from collections import Counter


def analyze_text_file(file_path):
    """Analyze text file and count letters."""
    # Check if file exists
    if not os.path.exists(file_path):
        return {"error": f"File not found: {file_path}"}

    try:
        # Read file content
        with open(file_path, encoding="utf-8") as f:
            content = f.read()

        # Count all characters
        total_chars = len(content)

        # Count only letters (Russian and English)
        russian_letters = (
            "абвгдеёжзийклмнопрстуфхцчшщъыьэюяАБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ"
        )
        english_letters = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"

        russian_count = sum(1 for char in content if char in russian_letters)
        english_count = sum(1 for char in content if char in english_letters)

        # Count each letter frequency
        letter_freq = Counter(
            char for char in content if char in russian_letters + english_letters
        )

        # Top 10 most common letters
        top_letters = dict(letter_freq.most_common(10))

        result = {
            "file": file_path,
            "total_characters": total_chars,
            "total_letters": russian_count + english_count,
            "russian_letters": russian_count,
            "english_letters": english_count,
            "top_10_letters": top_letters,
            "lines": content.count("\n") + 1,
            "words": len(content.split()),
        }

        # Print result as JSON
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return result

    except Exception as e:
        error_msg = f"Error analyzing file: {str(e)}"
        print(json.dumps({"error": error_msg}))
        return {"error": error_msg}


def main():
    """Main entry point."""
    # Get input file from environment variable or command line
    # Check both uppercase and lowercase versions
    input_file = os.environ.get("INPUT_FILE", "") or os.environ.get("input_file", "")

    if not input_file and len(sys.argv) > 1:
        input_file = sys.argv[1]

    if not input_file:
        # Default test file
        input_file = "/shared/test_text.txt"

    print(f"Analyzing file: {input_file}", file=sys.stderr)
    result = analyze_text_file(input_file)

    # Exit with appropriate code
    if "error" in result:
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
