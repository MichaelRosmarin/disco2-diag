#!/usr/bin/env bash
# Bring up a WiFi access point on wlan0 using NetworkManager (Raspberry Pi OS Bookworm+).
#
#   sudo bash deploy/hotspot.sh <ssid> <password>       create/replace and start the hotspot
#   sudo bash deploy/hotspot.sh off                     drop back to normal WiFi now
#
# The Pi has one radio, so it is either a client of a known network or the hotspot, never
# both. The known networks (the one from Raspberry Pi Imager, anything added since) are given
# a higher autoconnect priority than the hotspot, so:
#   - at home / the office the Pi joins that network as before (updates, SSH as usual)
#   - anywhere else (the car) NetworkManager finds nothing it knows and raises the hotspot
# Phones that join reach the dashboard at http://10.42.0.1/ (or http://disco2.local/).
#
# Running this over SSH from the home network drops the session: the radio switches to AP
# mode. Join the hotspot from a phone to check it, or just power-cycle the Pi at home to get
# it back on the house WiFi.
set -euo pipefail
CON=d2dash-hotspot

if [[ "${1:-}" == "off" ]]; then
  nmcli con down "$CON" 2>/dev/null || true
  nmcli con modify "$CON" connection.autoconnect no 2>/dev/null || true
  echo "hotspot stopped; the Pi will rejoin a known network"
  exit 0
fi

SSID=${1:-Disco2}
PSK=${2:-}
if [[ ${#PSK} -lt 8 ]]; then
  echo "usage: $0 <ssid> <password-of-8-or-more-characters>   |   $0 off" >&2
  exit 1
fi

# known client networks win when they are in range
while IFS=: read -r name type; do
  [[ "$type" == "802-11-wireless" && "$name" != "$CON" ]] || continue
  mode=$(nmcli -g 802-11-wireless.mode con show "$name" 2>/dev/null || true)
  [[ "$mode" == "ap" ]] && continue
  nmcli con modify "$name" connection.autoconnect yes connection.autoconnect-priority 100 \
    connection.autoconnect-retries 0
done < <(nmcli -t -f NAME,TYPE con show)

if nmcli -t -f NAME con show | grep -qx "$CON"; then
  nmcli con delete "$CON"
fi
nmcli con add type wifi ifname wlan0 con-name "$CON" autoconnect yes ssid "$SSID" \
  802-11-wireless.mode ap 802-11-wireless.band bg ipv4.method shared \
  wifi-sec.key-mgmt wpa-psk wifi-sec.psk "$PSK" \
  connection.autoconnect-priority 10 connection.autoconnect-retries 0
nmcli con up "$CON"
echo "hotspot $SSID up on wlan0: dashboard at http://10.42.0.1/"
echo "at home the Pi goes back to the house WiFi on its own; 'sudo bash deploy/hotspot.sh off' forces that now"
