"""Interactive helper to set up Google Analytics MCP credentials.

This wraps `gcloud auth application-default login` with the right scopes,
runs the browser sign-in, and prints the path you'll plug into
`~/.claude.json` as GOOGLE_APPLICATION_CREDENTIALS.

The helper looks for OAuth client credentials in this priority order:

  (1) The sibling Google Ads MCP's google-ads.yaml
      (~/Projects/mcp/googleads/google-ads.yaml). If found, reuses the
      client_id and client_secret already in there — no JSON download
      needed.

  (2) An OAuth client JSON file you downloaded from the Google Cloud
      Console (APIs & Services -> Credentials -> Desktop app -> Download).

  (3) Existing ADC: if you've already run gcloud auth previously, just
      reuse it without touching anything.

Run from the repo root:
    uv run setup_credentials.py
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

SCOPES = [
    "https://www.googleapis.com/auth/analytics.readonly",
    "https://www.googleapis.com/auth/cloud-platform",
]
DEFAULT_ADC_PATH = (
    Path.home() / ".config" / "gcloud" / "application_default_credentials.json"
)
ADS_YAML_PATH = (
    Path.home() / "Projects" / "mcp" / "googleads" / "google-ads.yaml"
)


def ask(prompt: str, default: str | None = None) -> str:
    suffix = f" [{default}]" if default else ""
    value = input(f"{prompt}{suffix}: ").strip()
    return value or (default or "")


def _client_json_from_ads_yaml() -> dict | None:
    """If the sibling Ads MCP's yaml is present, build the OAuth client JSON
    structure gcloud expects. Returns None if the yaml is missing or doesn't
    contain the needed keys."""
    if not ADS_YAML_PATH.is_file():
        return None
    try:
        import yaml
    except ImportError:
        return None
    data = yaml.safe_load(ADS_YAML_PATH.read_text()) or {}
    client_id = data.get("client_id")
    client_secret = data.get("client_secret")
    if not client_id or not client_secret:
        return None
    return {
        "installed": {
            "client_id": client_id,
            "client_secret": client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": ["http://localhost"],
        }
    }


def main() -> None:
    print("\n=== Google Analytics MCP credential setup ===\n")

    if not shutil.which("gcloud"):
        print("ERROR: gcloud CLI not found on PATH.")
        print("  Install with: brew install --cask google-cloud-sdk")
        sys.exit(1)

    if DEFAULT_ADC_PATH.is_file():
        print(f"Found existing ADC file at: {DEFAULT_ADC_PATH}")
        reuse = ask("Reuse it without re-authenticating? (y/N)", "n").lower()
        if reuse.startswith("y"):
            _verify_and_finish(DEFAULT_ADC_PATH)
            return

    # Pick the OAuth client config — auto-detect from Ads yaml, or ask.
    print()
    print("Step 1/3 — OAuth client")
    ads_client_config = _client_json_from_ads_yaml()
    tmp_client_path: Path | None = None
    if ads_client_config:
        print(f"  ✓ Detected OAuth client in {ADS_YAML_PATH}")
        print("    Reusing it for the GA Analytics auth — no download needed.")
        # Write a temp JSON file gcloud can read.
        tmp = tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, prefix="ga_oauth_client_"
        )
        json.dump(ads_client_config, tmp)
        tmp.close()
        tmp_client_path = Path(tmp.name)
        client_path = str(tmp_client_path)
    else:
        print("  No Ads yaml found at the expected sibling path:")
        print(f"    {ADS_YAML_PATH}")
        print("  Fall back: provide an OAuth client JSON file path.")
        print(
            "  (Download from https://console.cloud.google.com/apis/credentials)"
        )
        client_path = ask("Path to OAuth client JSON")
        if not client_path or not Path(client_path).is_file():
            print(f"ERROR: not a file: {client_path}")
            sys.exit(1)

    print()
    print("Step 2/3 — Enable required APIs in the Google Cloud project")
    print("  Open: https://console.cloud.google.com/apis/library")
    print(
        "  Search for and enable BOTH (one-time, only one teammate needs to):"
    )
    print("    - Google Analytics Data API")
    print("    - Google Analytics Admin API")
    input("  Press Enter when both are enabled...")

    print()
    print("Step 3/3 — Browser authorization")
    print("  A browser window will open. Sign in with the Google account that")
    print("  has access to your GA4 properties, then click 'Allow'.\n")
    input("  Press Enter to launch the browser...")

    cmd = [
        "gcloud",
        "auth",
        "application-default",
        "login",
        f"--scopes={','.join(SCOPES)}",
        f"--client-id-file={client_path}",
    ]
    print(f"  Running gcloud auth flow...\n")
    result = subprocess.run(cmd)

    # Clean up the temp file regardless of success/failure.
    if tmp_client_path and tmp_client_path.is_file():
        tmp_client_path.unlink()

    if result.returncode != 0:
        print("ERROR: gcloud auth failed.")
        sys.exit(1)

    if not DEFAULT_ADC_PATH.is_file():
        print(f"ERROR: ADC file not found at {DEFAULT_ADC_PATH} after auth.")
        sys.exit(1)

    _verify_and_finish(DEFAULT_ADC_PATH)


def _verify_and_finish(adc_path: Path) -> None:
    try:
        data = json.loads(adc_path.read_text())
    except Exception as exc:
        print(f"ERROR: couldn't parse {adc_path}: {exc}")
        sys.exit(1)

    if "refresh_token" not in data and data.get("type") != "service_account":
        print("WARNING: no refresh_token in the ADC file. The MCP may need")
        print("re-auth often. Re-run this script if queries start failing.")

    print()
    print("✓ ADC ready.")
    print(f"  Path: {adc_path}")
    print()
    print(
        "Plug this into ~/.claude.json under env.GOOGLE_APPLICATION_CREDENTIALS:"
    )
    print(f'  "GOOGLE_APPLICATION_CREDENTIALS": "{adc_path}"')
    print()
    print("Smoke test:")
    print(
        '  GOOGLE_APPLICATION_CREDENTIALS="'
        + str(adc_path)
        + '" uv run python -c "from google.analytics.admin import '
        "AnalyticsAdminServiceClient; c = AnalyticsAdminServiceClient(); "
        'print([a.account for a in c.list_account_summaries()])"'
    )


if __name__ == "__main__":
    main()
