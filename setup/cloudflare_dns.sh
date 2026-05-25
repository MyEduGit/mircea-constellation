#!/usr/bin/env bash
set -euo pipefail
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "$REPO_ROOT/.cloudflare.env"
: "${CF_API_TOKEN:?}" "${CF_ZONE_ID:?}" "${CF_ZONE:?}" "${TARGET_IP:?}"
DRY_RUN=false; [[ "${1:-}" == "--dry-run" ]] && DRY_RUN=true
CF_API="https://api.cloudflare.com/client/v4"
PAYLOAD=$(jq -n --arg ip "$TARGET_IP" --arg zone "$CF_ZONE" '{"type":"A","name":$zone,"content":$ip,"ttl":1,"proxied":true}')
if $DRY_RUN; then echo "[dry-run] $CF_ZONE -> $TARGET_IP (proxied)"; exit 0; fi
existing=$(curl -sS -H "Authorization: Bearer $CF_API_TOKEN" -H "Content-Type: application/json" "$CF_API/zones/$CF_ZONE_ID/dns_records?type=A&name=$CF_ZONE")
record_id=$(echo "$existing" | jq -r '.result[0].id // empty')
current_ip=$(echo "$existing" | jq -r '.result[0].content // empty')
if [[ -n "$record_id" ]]; then
  response=$(curl -sS -X PUT -H "Authorization: Bearer $CF_API_TOKEN" -H "Content-Type: application/json" "$CF_API/zones/$CF_ZONE_ID/dns_records/$record_id" --data "$PAYLOAD")
else
  response=$(curl -sS -X POST -H "Authorization: Bearer $CF_API_TOKEN" -H "Content-Type: application/json" "$CF_API/zones/$CF_ZONE_ID/dns_records" --data "$PAYLOAD")
fi
echo "$response" | jq -r 'if .success then "Done: \(.result.name) -> \(.result.content)" else "ERROR: \(.errors)" end'
