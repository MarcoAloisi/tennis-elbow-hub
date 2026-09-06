#!/bin/bash
# Nightly local safety net for the media dir (outfits/guides/avatars).
# Protects against accidental deletion or a bad deploy, NOT disk failure —
# this is a same-disk tarball, not off-site backup.
#
# Install once: crontab -e (as a user that can read /var/www/te4/media)
#   0 3 * * * /var/www/te4/infra/backup-media.sh >> /var/log/te4-backup.log 2>&1

set -e

MEDIA_DIR=/var/www/te4/media
BACKUP_DIR=/var/backups/te4-media
RETENTION_DAYS=7

mkdir -p "$BACKUP_DIR"
tar -czf "$BACKUP_DIR/media-$(date +%F).tar.gz" -C /var/www/te4 media

find "$BACKUP_DIR" -name 'media-*.tar.gz' -mtime "+$RETENTION_DAYS" -delete

echo "$(date -Iseconds) backed up $MEDIA_DIR"
