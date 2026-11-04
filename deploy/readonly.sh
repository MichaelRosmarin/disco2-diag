#!/usr/bin/env bash
# Toggle the Raspberry Pi OS overlay filesystem (root mounted read-only, writes go to RAM).
# With this on, yanking power never corrupts the SD card. Session logs still persist because
# /var/lib/d2dash is bind-mounted from a small writable partition of the same card.
#
#   sudo bash deploy/readonly.sh enable    # then reboot
#   sudo bash deploy/readonly.sh disable   # before apt upgrades or code updates, then reboot
set -euo pipefail
MODE=${1:-status}
case "$MODE" in
  enable)
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
