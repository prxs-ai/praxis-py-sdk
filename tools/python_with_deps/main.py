#!/usr/bin/env python3
"""Python tool with dependencies - demonstrates pip install in Dagger container.
Uses requests library to fetch data and analyze it.
"""

import datetime
import json
import sys
from pathlib import Path


def fetch_and_analyze_data(url: str) -> dict:
    """Fetch data from URL and analyze it."""
    try:
        import requests

        print(f"Fetching data from: {url}")
        response = requests.get(url, timeout=10)
        response.raise_for_status()

        # Basic analysis
        content = response.text
        headers = dict(response.headers)

        analysis = {
            "url": url,
            "status_code": response.status_code,
            "content_length": len(content),
            "content_type": headers.get("content-type", "unknown"),
            "server": headers.get("server", "unknown"),
            "lines": len(content.split("\n")),
            "words": len(content.split()),
            "has_json": content.strip().startswith("{")
            or content.strip().startswith("["),
            "has_html": "<html" in content.lower()
            or "<!doctype html" in content.lower(),
            "response_time_ms": response.elapsed.total_seconds() * 1000,
        }

        # Try to parse as JSON if it looks like JSON
        if analysis["has_json"]:
            try:
                json_data = response.json()
                analysis["json_keys"] = (
                    list(json_data.keys()) if isinstance(json_data, dict) else "array"
                )
            except:
                analysis["json_parse_error"] = True

        result = {
            "success": True,
            "tool": "url_analyzer",
            "analysis": analysis,
            "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
        }

        # Save report
        reports_dir = Path("/shared/reports")
        reports_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = reports_dir / f"url_analysis_{timestamp}.json"

        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)

        print(f"Report saved to: {report_path}")
        return result

    except ImportError:
        return {
            "success": False,
            "error": "requests library not available - pip install may have failed",
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def main():
    """Main function - reads URL argument."""
    if len(sys.argv) != 2:
        print("Usage: python main.py <url>")
        sys.exit(1)

    url = sys.argv[1]
    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    result = fetch_and_analyze_data(url)

    # Print result as JSON
    print(json.dumps(result, indent=2))

    if not result.get("success", False):
        sys.exit(1)


if __name__ == "__main__":
    main()
