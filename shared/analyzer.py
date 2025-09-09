#!/usr/bin/env python3
"""
Simple analyzer tool for testing Dagger execution.
"""
import sys
import os
import json
from datetime import datetime

def analyze_file(file_path):
    """Analyze a text file and return statistics."""
    if not os.path.exists(file_path):
        return {"error": f"File not found: {file_path}"}
    
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Perform analysis
    stats = {
        "file": file_path,
        "timestamp": datetime.now().isoformat(),
        "size_bytes": len(content),
        "lines": len(content.split('\n')),
        "words": len(content.split()),
        "characters": len(content),
        "unique_words": len(set(content.lower().split())),
        "average_word_length": sum(len(word) for word in content.split()) / max(len(content.split()), 1)
    }
    
    # Save report
    report_name = f"analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    report_path = f"/shared/reports/{report_name}"
    
    # Ensure reports directory exists
    os.makedirs("/shared/reports", exist_ok=True)
    
    with open(report_path, 'w') as f:
        json.dump(stats, f, indent=2)
    
    print(f"Analysis complete! Report saved to: {report_path}")
    print(json.dumps(stats, indent=2))
    
    return stats

if __name__ == "__main__":
    # Get input file from environment variable or command line
    input_file = os.environ.get('input_file', '')
    
    if not input_file and len(sys.argv) > 1:
        input_file = sys.argv[1]
    
    if not input_file:
        input_file = "/shared/test_data.txt"  # Default file
    
    result = analyze_file(input_file)
    sys.exit(0 if "error" not in result else 1)