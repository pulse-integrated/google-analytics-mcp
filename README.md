# Google Analytics MCP Server — Pulse fork

[Pulse Integrated](https://github.com/pulse-integrated) fork of the official [googleanalytics/google-analytics-mcp](https://github.com/googleanalytics/google-analytics-mcp). Customized for use with Claude Code and paired with [pulse-integrated/google-ads-mcp](https://github.com/pulse-integrated/google-ads-mcp). Skip down to [Setup for Pulse teammates](#setup-for-pulse-teammates) for the install steps.

A local [MCP](https://modelcontextprotocol.io) server that connects an LLM (Claude Code in our case) to the Google Analytics Admin + Data APIs. Read-only.

## Tools

The server uses the
[Google Analytics Admin API](https://developers.google.com/analytics/devguides/config/admin/v1)
and
[Google Analytics Data API](https://developers.google.com/analytics/devguides/reporting/data/v1)
to provide several
[Tools](https://modelcontextprotocol.io/docs/concepts/tools) for use with LLMs.

### Retrieve account and property information 🟠

- `get_account_summaries`: Retrieves information about the user's Google
  Analytics accounts and properties.
- `get_property_details`: Returns details about a property.
- `list_google_ads_links`: Returns a list of links to Google Ads accounts for
  a property.

### Run core reports 📙

- `run_report`: Runs a Google Analytics report using the Data API.
- `run_funnel_report`: Runs a Google Analytics funnel report using the Data API.
- `get_custom_dimensions_and_metrics`: Retrieves the custom dimensions and
  metrics for a specific property.

### Run realtime reports ⏳

- `run_realtime_report`: Runs a Google Analytics realtime report using the
  Data API.

## Setup for Pulse teammates

> Pulse-specific instructions. Pairs with the Pulse fork of [google-ads-mcp](https://github.com/pulse-integrated/google-ads-mcp). Same `~/Projects/mcp/` parent folder convention. If a teammate has already set up the Google Ads MCP on this Mac, most of the prerequisites are already done.

### Prerequisites

- **Claude Code installed** (not the regular Claude desktop app — different installer)
- **Homebrew installed**
- **A user account with access** to the GA4 properties you want to query (Pulse defaults to Sean's identity, since he has property-level access across our managed accounts)

### Steps

1. **Install gcloud and uv** if you don't have them:

   ```bash
   brew install --cask google-cloud-sdk
   brew install uv
   ```

2. **Clone the repo** anywhere:

   ```bash
   git clone https://github.com/pulse-integrated/google-analytics-mcp.git
   cd google-analytics-mcp
   ```

3. **Install dependencies:**

   ```bash
   uv sync
   ```

4. **Enable the two GA APIs** in the GCP project (one-time, only needs to be done by one teammate):

   - https://console.cloud.google.com/apis/library/analyticsadmin.googleapis.com
   - https://console.cloud.google.com/apis/library/analyticsdata.googleapis.com

5. **Run the credential setup helper:**

   ```bash
   uv run setup_credentials.py
   ```

   The helper auto-detects the OAuth client credentials from the sibling Google Ads MCP setup (`~/Projects/mcp/googleads/google-ads.yaml`) if present, so no JSON download is needed when both MCPs share the same OAuth client. If the Ads yaml isn't there, the helper falls back to asking for an OAuth client JSON path — download one from https://console.cloud.google.com/apis/credentials (Desktop app type).

   The helper opens a browser. Sign in with the Google account that has GA4 access. When done, the script prints the path to your ADC file (typically `~/.config/gcloud/application_default_credentials.json`).

6. **Register the MCP with Claude Code.** Open `~/.claude.json` and add the entry to your top-level `mcpServers` block (merge alongside any existing entries like `google-ads`):

   ```json
   {
     "mcpServers": {
       "google-analytics": {
         "type": "stdio",
         "command": "/opt/homebrew/bin/uv",
         "args": [
           "--directory",
           "/absolute/path/to/google-analytics-mcp",
           "run",
           "analytics-mcp"
         ],
         "env": {
           "GOOGLE_APPLICATION_CREDENTIALS": "/Users/YOU/.config/gcloud/application_default_credentials.json"
         }
       }
     }
   }
   ```

7. **Restart Claude Code** so the new MCP loads.

8. **Smoke test** from a terminal in the repo root:

   ```bash
   GOOGLE_APPLICATION_CREDENTIALS="$HOME/.config/gcloud/application_default_credentials.json" \
     uv run python -c "from google.analytics.admin import AnalyticsAdminServiceClient; \
     c = AnalyticsAdminServiceClient(); \
     print([(a.display_name, a.account) for a in c.list_account_summaries()])"
   ```

   You should see a list of `(account_name, account_id)` pairs. That confirms the MCP can reach the GA4 Admin API. If it errors, the message usually points at the fix (often a missing scope on the OAuth flow).

### Trade-offs worth knowing

- **Shared identity:** if all teammates use the same ADC file (e.g. Sean's), reports will look like Sean made them in audit logs. For read-only reporting this is fine.
- **API enablement is GCP-project-wide:** enabling the two GA APIs in the project covers every teammate using that OAuth client. Only one person needs to do step 5.
- **No mutation tools:** this MCP is read-only. We're not building goals, audiences, or admin mutations into it for now.

---

## Tracking upstream

This fork tracks [googleanalytics/google-analytics-mcp](https://github.com/googleanalytics/google-analytics-mcp) as `upstream`. To pull in updates from Google:

```bash
git remote add upstream https://github.com/googleanalytics/google-analytics-mcp.git  # one-time, if not already set
git fetch upstream
git merge upstream/main
```

Tools in `analytics_mcp/` are intentionally left unchanged so the merge stays clean. Pulse-specific files (`context.md`, `setup_credentials.py`, the "Setup for Pulse teammates" README section) are additive and don't touch upstream paths.

## License

[Apache 2.0](LICENSE), inherited from upstream.
