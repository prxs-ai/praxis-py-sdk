#!/usr/bin/env python3
"""
Simple Python tool for testing Dagger execution.
Processes a text file and generates a report.
"""

import sys
import json
import datetime
from pathlib import Path

def analyze_text(input_file: str) -> dict:
    """Analyze text file and return statistics."""
    try:
        file_path = Path(input_file)
        if not file_path.exists():
            return {
                "success": False,
                "error": f"File not found: {input_file}"
            }
        
        # Read file content
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Simple analysis
        lines = content.split('\n')
        words = content.split()
        chars = len(content)
        
        # Count some interesting stats
        sentences = len([s for s in content.split('.') if s.strip()])
        paragraphs = len([p for p in content.split('\n\n') if p.strip()])
        
        result = {
            "success": True,
            "file": str(file_path),
            "analysis": {
                "lines": len(lines),
                "words": len(words),
                "characters": chars,
                "sentences": sentences,
                "paragraphs": paragraphs,
                "average_words_per_line": len(words) / len(lines) if lines else 0,
                "average_chars_per_word": chars / len(words) if words else 0
            },
            "timestamp": datetime.datetime.utcnow().isoformat() + "Z"
        }
        
        # Save report to shared directory
        reports_dir = Path("/shared/reports")
        reports_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = reports_dir / f"text_analysis_{timestamp}.json"
        
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        
        print(f"Report saved to: {report_path}")
        return result
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

def main():
    """Main function - reads input file argument."""
    if len(sys.argv) != 2:
        print("Usage: python main.py <input_file>")
        sys.exit(1)
    
    input_file = sys.argv[1]
    result = analyze_text(input_file)
    
    # Print result as JSON
    print(json.dumps(result, indent=2))
    
    if not result.get("success", False):
        sys.exit(1)

if __name__ == "__main__":
    main()