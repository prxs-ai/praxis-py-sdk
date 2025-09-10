#!/usr/bin/env python3
import os
import json
import sys
from datetime import datetime


def _json_print(payload):
    print(json.dumps(payload, ensure_ascii=False))


def create_openai_client():
    """Create OpenAI client.

    - If Azure vars provided, use AzureOpenAI with api_version and endpoint.
    - Else use OpenAI with optional base_url.
    """
    try:
        from openai import OpenAI, AzureOpenAI
    except Exception as e:
        _json_print({"status": "error", "error": f"Failed to import openai client: {e}"})
        sys.exit(0)

    # Azure detection
    az_endpoint = os.environ.get("AZURE_OPENAI_ENDPOINT")
    az_key = os.environ.get("AZURE_OPENAI_API_KEY")
    az_version = os.environ.get("AZURE_OPENAI_API_VERSION") or "2024-02-15-preview"
    if az_endpoint and az_key:
        try:
            return AzureOpenAI(api_key=az_key, api_version=az_version, azure_endpoint=az_endpoint)
        except Exception as e:
            _json_print({"status": "error", "error": f"Failed to initialize AzureOpenAI client: {e}"})
            sys.exit(0)

    # Regular OpenAI
    api_key = os.environ.get("OPENAI_API_KEY")
    base_url = os.environ.get("OPENAI_BASE_URL")
    if not api_key:
        _json_print({"status": "error", "error": "OPENAI_API_KEY is not set"})
        sys.exit(0)
    try:
        if base_url:
            return OpenAI(api_key=api_key, base_url=base_url)
        return OpenAI(api_key=api_key)
    except Exception as e:
        _json_print({"status": "error", "error": f"Failed to initialize OpenAI client: {e}"})
        sys.exit(0)


def main():
    # Arguments come via env (Dagger engine injects args as env)
    text = os.environ.get("text") or os.environ.get("TEXT") or ""
    tone = os.environ.get("tone") or os.environ.get("TONE") or "confident, friendly"
    length = os.environ.get("length") or os.environ.get("LENGTH") or "medium"
    audience = os.environ.get("audience") or os.environ.get("AUDIENCE") or "general audience"
    model = os.environ.get("model") or os.environ.get("OPENAI_MODEL") or "gpt-4o"

    if not text:
        _json_print({
            "status": "error",
            "error": "No input text provided (env 'text')"
        })
        return

    client = create_openai_client()

    system_prompt = (
        "You are an expert English copywriter. Rewrite the user's text in a clear,"
        " natural style while preserving meaning. Always write in English."
        " Respect the requested tone, length, and audience. Output only the rewritten"
        " text, without commentary."
    )

    user_prompt = (
        f"Rewrite the following text in English.\n\n"
        f"Tone: {tone}\n"
        f"Desired length: {length}\n"
        f"Audience: {audience}\n\n"
        f"Text:\n{text}"
    )

    try:
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.5,
        )
        rewritten = resp.choices[0].message.content.strip()
        result = {
            "status": "success",
            "tool": "gpt_rewriter",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "input": {
                "tone": tone,
                "length": length,
                "audience": audience,
                "model": model,
            },
            "rewritten_text": rewritten,
        }

        # Save to /shared/reports as a convenience (host-mounted)
        try:
            reports_dir = "/shared/reports"
            os.makedirs(reports_dir, exist_ok=True)
            fname = f"gpt_rewriter_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
            fpath = os.path.join(reports_dir, fname)
            with open(fpath, "w", encoding="utf-8") as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            # annotate and print where saved
            result["saved_to_path"] = fpath
            print(json.dumps({"status":"info","message":"REPORT SAVED","path":fpath}, ensure_ascii=False))
        except Exception as _e:
            print(json.dumps({"status":"warn","message":f"Could not save report: {_e}"}, ensure_ascii=False))

        _json_print(result)
    except Exception as e:
        _json_print({
            "status": "error",
            "error": f"OpenAI call failed: {e}",
        })


if __name__ == "__main__":
    main()
