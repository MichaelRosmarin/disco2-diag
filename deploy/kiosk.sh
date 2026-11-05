#!/usr/bin/env bash
# Boot straight into the dashboard on an HDMI touchscreen (stage 3).
#
# Installs cage (a single-app Wayland compositor) and Chromium, and a systemd service that
# starts them on tty1 as the service user, full-screen on http://localhost/. No desktop,
# no window manager; the Pi 3 copes because nothing else is drawing.
#
#   sudo bash deploy/kiosk.sh            install + enable
#   sudo bash deploy/kiosk.sh disable    back to a plain console on tty1
#
# A screen that is unplugged is fine: cage waits for an output. Chromium keeps its profile
# in /var/lib/d2dash/kiosk so the read-only root overlay does not fight it.
set -euo pipefail

SERVICE_USER="${SERVICE_USER:-pi}"
URL="${KIOSK_URL:-http://localhost/}"
UNIT=/etc/systemd/system/d2dash-kiosk.service

if [[ "${1:-}" == "disable" ]]; then
  systemctl disable --now d2dash-kiosk.service || true
  systemctl enable getty@tty1.service
  echo "kiosk disabled"
  exit 0
fi

echo "==> packages (cage + chromium, ~150 MB)"
apt-get install -y -q cage chromium seatd fonts-dejavu-core
usermod -aG video,input,render,seat "$SERVICE_USER" 2>/dev/null || usermod -aG video,input "$SERVICE_USER"
install -d -o "$SERVICE_USER" -g "$SERVICE_USER" /var/lib/d2dash/kiosk

echo "==> systemd unit"
cat > "$UNIT" <<EOF
[Unit]
Description=d2dash kiosk (Chromium in cage on the HDMI touchscreen)
After=d2dash.service systemd-user-sessions.service
Wants=d2dash.service
Conflicts=getty@tty1.service

[Service]
User=$SERVICE_USER
PAMName=login
TTYPath=/dev/tty1
StandardInput=tty
StandardOutput=journal
Environment=XDG_RUNTIME_DIR=/run/user/%U
Environment=WLR_LIBINPUT_NO_DEVICES=1
ExecStartPre=/bin/sh -c 'for i in \$(seq 1 30); do curl -fs $URL >/dev/null && exit 0; sleep 1; done; exit 0'
ExecStart=/usr/bin/cage -d -- /usr/bin/chromium --kiosk --noerrdialogs --disable-infobars --disable-session-crashed-bubble \\
  --ozone-platform=wayland --enable-features=OverlayScrollbar --touch-events=enabled --password-store=basic \\
  --user-data-dir=/var/lib/d2dash/kiosk --check-for-update-interval=31536000 --disable-features=TranslateUI $URL
Restart=always
RestartSec=3

[Install]
WantedBy=graphical.target
EOF

systemctl daemon-reload
systemctl disable getty@tty1.service
systemctl enable --now d2dash-kiosk.service
systemctl set-default graphical.target
echo "kiosk enabled; the dashboard appears on HDMI within ~20 s of boot. 'sudo bash deploy/kiosk.sh disable' undoes it."
