#!/bin/sh
# Install as /etc/letsencrypt/renewal-hooks/deploy/netbird-caddy.sh (mode 755).
# certbot runs every script in that directory after a successful renewal, with
# RENEWED_LINEAGE set to the live/<name> directory of the certificate that changed.
# Caddy was given file paths, so it must be restarted to pick up the new files.
set -eu
case "${RENEWED_LINEAGE:-}" in
  */net.lexipedia.xyz) ;;
  *) exit 0 ;;
esac
cd /opt/netbird-server
exec docker compose restart caddy
