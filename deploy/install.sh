#!/usr/bin/env bash
# One-shot installer for d2dash on Raspberry Pi OS Lite (Bookworm or later), Pi 3B+/4.
#
#   sudo bash deploy/install.sh
#
# What it does:
#   - installs system packages and a Python venv under /opt/d2dash
#   - installs the openostler platform + d2diag vehicle pack + this dashboard
#   - puts the pi user in the dialout group (serial port access)
#   - installs and enables the d2dash systemd service
#   - (optional) brings up a WiFi hotspot "Disco2" so a phone can reach the dashboard
#   - (optional) enables the read-only overlay filesystem so power cuts can't corrupt the SD
#
# Re-running is safe; everything is idempotent.
set -euo pipefail

APP_DIR=/opt/d2dash
REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
SERVICE_USER=${SUDO_USER:-pi}
HOTSPOT_SSID=${HOTSPOT_SSID:-Disco2}
HOTSPOT_PSK=${HOTSPOT_PSK:-}           # export HOTSPOT_PSK=... with ENABLE_HOTSPOT=yes
ENABLE_HOTSPOT=${ENABLE_HOTSPOT:-no}   # the hotspot is normally a separate step: deploy/hotspot.sh
ENABLE_READONLY=${ENABLE_READONLY:-no}   # set to yes once everything works

if [[ $EUID -ne 0 ]]; then echo "run with sudo"; exit 1; fi

echo "==> apt packages"
apt-get update -q
apt-get install -y -q python3 python3-venv python3-pip git network-manager parted

echo "==> serial port access for $SERVICE_USER"
usermod -aG dialout "$SERVICE_USER"

echo "==> python venv at $APP_DIR"
mkdir -p "$APP_DIR"
if [[ ! -x "$APP_DIR/venv/bin/python" ]]; then
  python3 -m venv "$APP_DIR/venv"
fi
"$APP_DIR/venv/bin/pip" install -q --upgrade pip wheel
"$APP_DIR/venv/bin/pip" install -q \
  "openostler @ git+https://github.com/openostler/ostler@main" \
  "d2diag @ git+https://github.com/openostler/ostler-pack-lr-d2@main"
"$APP_DIR/venv/bin/pip" install -q -e "$REPO_DIR"

echo "==> udev: /dev/kline (FTDI cable) and /dev/sensors (ESP32 board)"
install -m 0644 "$REPO_DIR/deploy/99-d2dash.rules" /etc/udev/rules.d/99-d2dash.rules
udevadm control --reload-rules && udevadm trigger --subsystem-match=tty || true

echo "==> data dirs"
install -d -o "$SERVICE_USER" -g "$SERVICE_USER" /var/lib/d2dash/logs
install -d -o "$SERVICE_USER" -g "$SERVICE_USER" /etc/d2dash
if [[ ! -f /etc/d2dash/d2dash.env ]]; then
  cat > /etc/d2dash/d2dash.env <<EOF
# d2dash runtime configuration (systemd EnvironmentFile)
# K-line cable. /dev/kline is the udev name for the FTDI cable; "auto" also works with one device.
D2DASH_PORT=/dev/kline
# ESP32 sensor board: /dev/sensors (udev), "auto", or "none" to disable
D2DASH_SENSORS_PORT=/dev/sensors
D2DASH_HTTP_PORT=80
D2DASH_LOG_DIR=/var/lib/d2dash/logs
# set to 1 to run against the built-in simulator instead of the car
D2DASH_SIMULATE=0
EOF
else
  grep -q D2DASH_SENSORS_PORT /etc/d2dash/d2dash.env || echo "D2DASH_SENSORS_PORT=/dev/sensors" >> /etc/d2dash/d2dash.env
  sed -i 's#^D2DASH_PORT=/dev/ttyUSB0$#D2DASH_PORT=/dev/kline#' /etc/d2dash/d2dash.env
fi

echo "==> systemd service"
sed "s|@APP_DIR@|$APP_DIR|g; s|@USER@|$SERVICE_USER|g" \
  "$REPO_DIR/deploy/d2dash.service" > /etc/systemd/system/d2dash.service
# port 80 comes from AmbientCapabilities in the unit; undo the old setcap on the system python
setcap -r "$(readlink -f "$APP_DIR/venv/bin/python")" 2>/dev/null || true
systemctl daemon-reload
systemctl enable d2dash.service
systemctl restart d2dash.service

if [[ "$ENABLE_HOTSPOT" == "yes" ]]; then
  echo "==> wifi hotspot $HOTSPOT_SSID"
  bash "$REPO_DIR/deploy/hotspot.sh" "$HOTSPOT_SSID" "$HOTSPOT_PSK"
fi

if [[ "$ENABLE_READONLY" == "yes" ]]; then
  echo "==> enabling overlay read-only root (reboot required)"
  bash "$REPO_DIR/deploy/readonly.sh" enable
fi

echo
echo "Done. Dashboard: http://disco2.local/  (or http://10.42.0.1/ on the hotspot)"
echo "Logs: journalctl -u d2dash -f"

# Ghostty/kitty terminals advertise a TERM the Pi does not know ("terminal is not fully
# functional" from pagers). Fall back to xterm-256color for interactive shells.
if ! grep -q "d2dash: unknown TERM" "/home/$SERVICE_USER/.bashrc" 2>/dev/null; then
  cat >> "/home/$SERVICE_USER/.bashrc" <<'EOB'
# d2dash: unknown TERM fallback
case "$TERM" in xterm-ghostty|xterm-kitty) infocmp "$TERM" >/dev/null 2>&1 || export TERM=xterm-256color ;; esac
EOB
fi
