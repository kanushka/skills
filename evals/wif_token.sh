#!/usr/bin/env bash
# Print a short-lived Anthropic access token for this GitHub Actions run via
# Workload Identity Federation. Each call mints a fresh GitHub OIDC token,
# because Anthropic accepts each one only once.
set -euo pipefail

: "${ACTIONS_ID_TOKEN_REQUEST_URL:?needs permissions: id-token: write}"
: "${ANTHROPIC_FEDERATION_RULE_ID:?}" "${ANTHROPIC_ORGANIZATION_ID:?}" "${ANTHROPIC_SERVICE_ACCOUNT_ID:?}"

jwt=$(curl -fsS -H "Authorization: Bearer $ACTIONS_ID_TOKEN_REQUEST_TOKEN" \
  "$ACTIONS_ID_TOKEN_REQUEST_URL&audience=https://api.anthropic.com" | jq -r .value)

jq -n \
  --arg assertion "$jwt" \
  --arg rule "$ANTHROPIC_FEDERATION_RULE_ID" \
  --arg org "$ANTHROPIC_ORGANIZATION_ID" \
  --arg sa "$ANTHROPIC_SERVICE_ACCOUNT_ID" \
  --arg ws "${ANTHROPIC_WORKSPACE_ID:-}" \
  '{grant_type: "urn:ietf:params:oauth:grant-type:jwt-bearer", assertion: $assertion,
    federation_rule_id: $rule, organization_id: $org, service_account_id: $sa}
   + (if $ws == "" then {} else {workspace_id: $ws} end)' |
  curl -fsS https://api.anthropic.com/v1/oauth/token -H "content-type: application/json" -d @- |
  jq -er .access_token
