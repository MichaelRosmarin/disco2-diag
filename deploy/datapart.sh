#!/usr/bin/env bash
# Put /var/lib/d2dash (session logs, state) on its own writable storage so the root filesystem
# can go read-only (deploy/readonly.sh) without losing every drive's CSV at key-off.
#
# The storage is a USB flash drive: any size, it is wiped. A USB stick beats a partition on
# the SD card because a corrupt stick can never stop the Pi booting, and it can be pulled and
# read on a laptop.
#
#   lsblk                                   find the stick (e.g. sda, 14.9G, no mountpoint)
#   sudo bash deploy/datapart.sh /dev/sda   format it and move the logs there
#   sudo bash deploy/datapart.sh status
set -euo pipefail
LABEL=D2DATA
MNT=/var/lib/d2dash
SERVICE_USER=${SERVICE_USER:-pi}
DEV=${1:-}

if [[ "$DEV" == "status" || -z "$DEV" ]]; then
  if mountpoint -q "$MNT"; then
    echo "logs are on: $(findmnt -no SOURCE "$MNT") ($(findmnt -no FSTYPE "$MNT"), $(df -h --output=avail "$MNT" | tail -1 | tr -d ' ') free)"
  else
    echo "logs are on the root filesystem (no data drive). Usage: $0 /dev/sdX"
  fi
  exit 0
fi
[[ $EUID -eq 0 ]] || { echo "run with sudo"; exit 1; }
[[ -b "$DEV" ]] || { echo "$DEV is not a block device; see lsblk"; exit 1; }
case "$DEV" in /dev/mmcblk*) echo "refusing to touch the SD card the system runs from"; exit 1 ;; esac
if findmnt -rno TARGET --source "$DEV" >/dev/null 2>&1 || findmnt -rno TARGET --source "${DEV}1" >/dev/null 2>&1; then
  echo "$DEV is mounted; unplug and replug it, or umount it first"; exit 1
fi

echo "This WIPES $DEV:"; lsblk -o NAME,SIZE,MODEL,FSTYPE,MOUNTPOINT "$DEV"
read -r -p "type YES to continue: " ok; [[ "$ok" == "YES" ]] || exit 1

echo "==> partition + ext4 (no journal: fewer writes, nothing on it matters if one file dies)"
wipefs -a "$DEV" >/dev/null
sgdisk --zap-all "$DEV" >/dev/null 2>&1 || true
parted -s "$DEV" mklabel gpt mkpart d2data ext4 1MiB 100%
sleep 1; partprobe "$DEV" || true; sleep 1
PART=$(lsblk -nrpo NAME "$DEV" | sed -n 2p)
mkfs.ext4 -q -F -L "$LABEL" -O ^has_journal "$PART"

echo "==> move existing logs"
systemctl stop d2dash.service || true
TMP=$(mktemp -d); mount "$PART" "$TMP"
if [[ -d "$MNT" ]]; then cp -a "$MNT"/. "$TMP"/; fi
umount "$TMP"; rmdir "$TMP"

echo "==> fstab (by label, boots fine without the stick)"
sed -i "\#[[:space:]]$MNT[[:space:]]#d" /etc/fstab
echo "LABEL=$LABEL  $MNT  ext4  defaults,noatime,nofail,x-systemd.device-timeout=5  0  2" >> /etc/fstab
install -d "$MNT"
systemctl daemon-reload
mount "$MNT"
chown -R "$SERVICE_USER:$SERVICE_USER" "$MNT"
systemctl start d2dash.service
echo "done: logs now on $PART at $MNT. The root filesystem can go read-only: sudo bash deploy/readonly.sh enable"
