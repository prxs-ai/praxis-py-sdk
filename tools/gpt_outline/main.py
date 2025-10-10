#!/usr/bin/env python3
import json
import os
import sys
from datetime import datetime


def jprint(payload):
    print(json.dumps(payload, ensure_ascii=False))


def create_openai_client():
    """Create OpenAI client.

    Supports Azure via AzureOpenAI if AZURE_* env vars provided.
    """
    try:
        from openai import AzureOpenAI, OpenAI
    except Exception as e:
        jprint({"status": "error", "error": f"Failed to import openai client: {e}"})
        sys.exit(0)

    az_endpoint = os.environ.get("AZURE_OPENAI_ENDPOINT")
    az_key = os.environ.get("AZURE_OPENAI_API_KEY")
    az_version = os.environ.get("AZURE_OPENAI_API_VERSION") or "2024-02-15-preview"
    if az_endpoint and az_key:
        try:
            return AzureOpenAI(
                api_key=az_key, api_version=az_version, azure_endpoint=az_endpoint
            )
        except Exception as e:
            jprint(
                {
                    "status": "error",
                    "error": f"Failed to initialize AzureOpenAI client: {e}",
                }
            )
            sys.exit(0)

    api_key = os.environ.get("OPENAI_API_KEY")
    base_url = os.environ.get("OPENAI_BASE_URL")
    if not api_key:
        jprint({"status": "error", "error": "OPENAI_API_KEY is not set"})
        sys.exit(0)
    try:
        if base_url:
            return OpenAI(api_key=api_key, base_url=base_url)
        return OpenAI(api_key=api_key)
    except Exception as e:
        jprint({"status": "error", "error": f"Failed to initialize OpenAI client: {e}"})
        sys.exit(0)


def main():
    topic = os.environ.get("topic") or os.environ.get("TOPIC") or ""
    primary_keyword = (
        os.environ.get("primary_keyword") or os.environ.get("PRIMARY_KEYWORD") or ""
    )
    model = os.environ.get("model") or os.environ.get("OPENAI_MODEL") or "gpt-4o"

    if not topic:
        jprint({"status": "error", "error": "No topic provided (env 'topic')"})
        return

    client = create_openai_client()

    system_prompt = (
        "You are an expert content strategist and SEO specialist."
        " Produce output strictly in English, structured as JSON."
    )
    user_prompt = (
        "Create a detailed blog outline for the given topic. Include:"
        " 1) a strong working title, 2) 6-10 section headings with short notes,"
        " 3) 10-15 SEO keywords (lowercase), 4) a brief 2-3 sentence summary.\n\n"
        f"Topic: {topic}\n"
        f"Primary keyword (optional): {primary_keyword}"
    )

    try:
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.6,
        )
        content = resp.choices[0].message.content.strip()
        # Try to parse as JSON, otherwise wrap as field
        try:
            parsed = json.loads(content)
            result = parsed
        except Exception:
            result = {"outline_text": content}

        payload = {
            "status": "success",
            "tool": "gpt_outline",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "input": {
                "topic": topic,
                "primary_keyword": primary_keyword,
                "model": model,
            },
            "result": result,
        }

        # Save to /shared/reports
        try:
            reports_dir = "/shared/reports"
            os.makedirs(reports_dir, exist_ok=True)
            fname = f"gpt_outline_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
            fpath = os.path.join(reports_dir, fname)
            with open(fpath, "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False, indent=2)
            payload["saved_to_path"] = fpath
            print(
                json.dumps(
                    {"status": "info", "message": "REPORT SAVED", "path": fpath},
                    ensure_ascii=False,
                )
            )
        except Exception as _e:
            print(
                json.dumps(
                    {"status": "warn", "message": f"Could not save report: {_e}"},
                    ensure_ascii=False,
                )
            )

        jprint(payload)
    except Exception as e:
        jprint({"status": "error", "error": f"OpenAI call failed: {e}"})


if __name__ == "__main__":
    main()
