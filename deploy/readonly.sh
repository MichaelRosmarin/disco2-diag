#!/usr/bin/env bash
# Toggle the Raspberry Pi OS overlay filesystem (root mounted read-only, writes go to RAM).
# With this on, yanking power never corrupts the SD card.
#
# NOT YET: session logs live in /var/lib/d2dash/logs, which is on the root filesystem, so with
# the overlay on every drive's CSV is lost at key-off. Until deploy/datapart.sh exists to put
# /var/lib/d2dash on its own writable partition, `enable` refuses unless FORCE=1 is set.
#
#   sudo bash deploy/readonly.sh enable    # then reboot
#   sudo bash deploy/readonly.sh disable   # before apt upgrades or code updates, then reboot
set -euo pipefail
MODE=${1:-status}
case "$MODE" in
  enable)
    if ! mountpoint -q /var/lib/d2dash && [[ "${FORCE:-0}" != "1" ]]; then
      echo "refusing: /var/lib/d2dash is on the root filesystem, so logs would be lost at every"
      echo "power-off with the overlay on. Set up the data partition first, or FORCE=1 to accept that."
      exit 1
    fi
    raspi-config nonint enable_overlayfs
    raspi-config nonint enable_bootro
    echo "overlay enabled; reboot to apply. Remember: disable before updating."
    ;;
  disable)
    raspi-config nonint disable_overlayfs
    raspi-config nonint disable_bootro
    echo "overlay disabled; reboot to apply."
    ;;
  status)
    if grep -q "overlayroot" /proc/cmdline 2>/dev/null || mount | grep -q "overlay on / "; then
      echo "overlay: ON (root is read-only)"
    else
      echo "overlay: OFF (root is writable)"
    fi
    ;;
  *) echo "usage: $0 enable|disable|status"; exit 1 ;;
esac
