#!/usr/bin/env bash
# Teach the Pi a WiFi network it should join whenever it is in range (home, office, a lodge).
#
#   sudo bash deploy/wifi.sh "<ssid>" "<password>"
#   sudo bash deploy/wifi.sh list
#
# Known networks are given priority over the Disco2 hotspot, so the hotspot only comes up
# where none of them is in range (the car). If you run this over the hotspot, the session
# drops as the radio switches; reconnect with `ssh pi@disco2.local` on the new network.
set -euo pipefail

if [[ "${1:-}" == "list" ]]; then
  nmcli -f NAME,TYPE,AUTOCONNECT-PRIORITY,ACTIVE con show | grep -E "NAME|wireless"
  exit 0
fi
SSID=${1:-}; PSK=${2:-}
if [[ -z "$SSID" || ${#PSK} -lt 8 ]]; then
  echo "usage: $0 \"<ssid>\" \"<password>\"   |   $0 list" >&2
  exit 1
fi

if nmcli -t -f NAME con show | grep -qx "$SSID"; then
  nmcli con modify "$SSID" wifi-sec.psk "$PSK" || true
else
  nmcli con add type wifi ifname wlan0 con-name "$SSID" ssid "$SSID" \
    wifi-sec.key-mgmt wpa-psk wifi-sec.psk "$PSK"
fi
nmcli con modify "$SSID" connection.autoconnect yes connection.autoconnect-priority 100 \
  connection.autoconnect-retries 0
echo "saved $SSID (priority 100); switching to it now"
nmcli con up "$SSID" || echo "not in range right now; it will connect when it is"
