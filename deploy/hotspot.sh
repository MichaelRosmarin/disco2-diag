#!/usr/bin/env bash
# Bring up a WiFi access point on wlan0 using NetworkManager (Raspberry Pi OS Bookworm+).
# Usage: sudo bash deploy/hotspot.sh <ssid> <password>
# The Pi gets 10.42.0.1; phones that join reach the dashboard at http://10.42.0.1/
set -euo pipefail
SSID=${1:-Disco2}
PSK=${2:-landrover}
CON=d2dash-hotspot

if nmcli -t -f NAME con show | grep -qx "$CON"; then
  nmcli con delete "$CON"
fi
nmcli con add type wifi ifname wlan0 con-name "$CON" autoconnect yes ssid "$SSID" \
  802-11-wireless.mode ap 802-11-wireless.band bg ipv4.method shared \
  wifi-sec.key-mgmt wpa-psk wifi-sec.psk "$PSK"
# the hotspot should win over any saved client network when the car is away from home
nmcli con modify "$CON" connection.autoconnect-priority 50
nmcli con up "$CON"
echo "hotspot $SSID up on wlan0 (10.42.0.1)"
