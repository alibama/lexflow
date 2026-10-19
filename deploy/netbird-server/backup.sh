#!/bin/sh
# Nightly backup of the NetBird state (small: a few MB) plus the config files.
# Install:  sudo cp backup.sh /opt/netbird-server/backup.sh && sudo chmod 700 /opt/netbird-server/backup.sh
# Cron:     0 4 * * * /opt/netbird-server/backup.sh >> /var/log/netbird-backup.log 2>&1
# The tarballs contain the IdP's user records and the store encryption key: copy them
# off the droplet (scp/rclone) and treat them like a private key.
set -eu
DIR=/opt/netbird-server
OUT=/var/backups/netbird
KEEP=14
VOL=netbird_netbird_data            # <compose project name>_<volume>; check with: docker volume ls
STAMP=$(date -u +%Y%m%dT%H%M%SZ)
WORK=$OUT/$STAMP
mkdir -p "$WORK"
# SQLite online backups of every *.db in the data dir (the server keeps running), then
# everything else (keys, state) copied as-is. The file names inside the volume are not
# documented ([unconfirmed]); the glob covers whatever is there.
docker run --rm -v "$VOL":/data:ro -v "$WORK":/out alpine:3.22 /bin/sh -c '
  apk add --no-cache sqlite >/dev/null &&
  for f in /data/*.db; do [ -e "$f" ] && sqlite3 "$f" ".backup /out/$(basename "$f")"; done;
  cd /data && find . -type f ! -name "*.db" ! -name "*.db-wal" ! -name "*.db-shm" -exec cp --parents {} /out/ \;'
cp "$DIR/config.yaml" "$DIR/dashboard.env" "$DIR/compose.yml" "$DIR/Caddyfile" "$WORK/"
cp "$DIR/.env" "$WORK/" 2>/dev/null || true
tar -C "$OUT" -czf "$OUT/netbird-$STAMP.tgz" "$STAMP"
rm -r "$WORK"
chmod 600 "$OUT/netbird-$STAMP.tgz"
ls -1t "$OUT"/netbird-*.tgz | tail -n +$((KEEP+1)) | xargs -r rm --
echo "ok $OUT/netbird-$STAMP.tgz $(du -h "$OUT/netbird-$STAMP.tgz" | cut -f1)"
