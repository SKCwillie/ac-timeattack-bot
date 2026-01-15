#!/usr/bin/env bash
set -euo pipefail

PORT="${1:-9600}"

echo "[info] Killing ALL TCP connections involving local port :${PORT} (all states)..."

# Get all TCP sockets, then keep only lines where local endpoint ends with :PORT
# Exclude LISTEN since those are not per-client connections.
sudo ss -Htn | awk -v p=":${PORT}" '
  $1 != "LISTEN" && $4 ~ p"$" { print $1, $4, $5 }
' | while read -r state local peer; do

  # ss formats can include IPv4-mapped IPv6: [::ffff:172.31.29.224]:9600
  # Normalize to plain "ip:port"
  local_clean="$(echo "$local" | sed -E 's/^\[::ffff:([0-9.]+)\]/\1/; s/^\[//; s/\]$//')"
  peer_clean="$(echo "$peer"  | sed -E 's/^\[::ffff:([0-9.]+)\]/\1/; s/^\[//; s/\]$//')"

  local_ip="${local_clean%:*}"
  local_port="${local_clean##*:}"
  peer_ip="${peer_clean%:*}"
  peer_port="${peer_clean##*:}"

  # Defensive: only act on the port we intend
  [[ "$local_port" == "$PORT" ]] || continue

  # Some weird states can show peer as "*" or empty; skip those
  if [[ -z "$peer_ip" || -z "$peer_port" || "$peer_ip" == "*" || "$peer_port" == "*" ]]; then
    echo "[skip] state=$state local=$local_clean peer=$peer_clean"
    continue
  fi

  echo "[kill] state=$state  src $local_ip sport=$local_port -> dst $peer_ip dport=$peer_port"
  sudo ss -K src "$local_ip" sport = "$local_port" dst "$peer_ip" dport = "$peer_port" || true
done

echo "[info] Remaining non-LISTEN sockets on :${PORT}:"
sudo ss -Htn | awk -v p=":${PORT}" '$1 != "LISTEN" && $4 ~ p"$" { print }' || true

