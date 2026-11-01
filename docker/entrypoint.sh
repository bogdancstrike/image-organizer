#!/bin/sh
# Run as PUID:PGID so organized files keep the host user's ownership (REQ-DEP-2).
set -e
PUID="${PUID:-1000}"
PGID="${PGID:-1000}"

if [ "$(id -u)" = "0" ]; then
  mkdir -p /data
  # only fix what is wrong; avoids a slow recursive chown on every start
  find /data \( ! -uid "$PUID" -o ! -gid "$PGID" \) -exec chown "$PUID:$PGID" {} + 2>/dev/null || true
  export HOME=/tmp
  exec gosu "$PUID:$PGID" "$@"
fi
exec "$@"
