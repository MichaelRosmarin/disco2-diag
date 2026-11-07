#!/usr/bin/env bash
# Remote hands on the Pi without pulling it out of the dash.
#
#   sudo bash deploy/remote.sh terminal '<password>'   web terminal on port 7681 (ttyd)
#   sudo bash deploy/remote.sh connect                 Raspberry Pi Connect (needs internet + a Pi ID)
#   sudo bash deploy/remote.sh off                     stop the web terminal
#
# Web terminal: a real shell on the Pi in a browser tab, http://disco2.local:7681/, protected
# by a username/password (user "pi"). It listens on every interface the Pi has, which in the
# car means the Ethernet socket in the dash and the Disco2 hotspot; it is never reachable from
# the internet because the Pi is never on one in the car. Claude can type into a browser tab,
# which is the point: plug a laptop into the dash socket, open the tab, and the Pi can be
# driven from the chat.
#
# Ethernet without a router: the eth0 profile gets a link-local address (169.254.x.x) when no
# DHCP server answers, so a bare cable to a laptop works and disco2.local resolves over it.
set -euo pipefail
SERVICE_USER=${SERVICE_USER:-pi}
PORT=${TTYD_PORT:-7681}
MODE=${1:-}

case "$MODE" in
  terminal)
    PW=${2:-}
    if [[ ${#PW} -lt 8 ]]; then echo "usage: $0 terminal '<password of 8+ chars>'" >&2; exit 1; fi
    echo "==> ttyd"
    if ! apt-get install -y -q ttyd 2>/dev/null; then
      # not packaged on Raspberry Pi OS Trixie: use the project's static binary, checksum verified
      VER=${TTYD_VERSION:-1.7.7}
      ARCH=$(uname -m); case "$ARCH" in aarch64) A=aarch64 ;; armv7l) A=armhf ;; x86_64) A=x86_64 ;; *) echo "no ttyd build for $ARCH"; exit 1 ;; esac
      TMP=$(mktemp -d)
      curl -fsSL -o "$TMP/ttyd" "https://github.com/tsl0922/ttyd/releases/download/$VER/ttyd.$A"
      curl -fsSL -o "$TMP/SHA256SUMS" "https://github.com/tsl0922/ttyd/releases/download/$VER/SHA256SUMS"
      (cd "$TMP" && grep " ttyd.$A\$" SHA256SUMS | sed "s/ttyd.$A/ttyd/" | sha256sum -c -)
      install -m 0755 "$TMP/ttyd" /usr/bin/ttyd
      rm -rf "$TMP"
      echo "ttyd $VER installed to /usr/bin/ttyd"
    fi
    install -d -m 0750 /etc/d2dash
    printf 'TTYD_CRED=%s:%s\n' "$SERVICE_USER" "$PW" > /etc/d2dash/ttyd.env
    chmod 0600 /etc/d2dash/ttyd.env
    cat > /etc/systemd/system/d2dash-ttyd.service <<EOF
[Unit]
Description=d2dash web terminal (ttyd on port $PORT)
After=network.target

[Service]
User=$SERVICE_USER
WorkingDirectory=/home/$SERVICE_USER
Environment=TERM=xterm-256color
EnvironmentFile=/etc/d2dash/ttyd.env
ExecStart=/usr/bin/ttyd -p $PORT -W -c \${TTYD_CRED} -t titleFixed="disco2" -t fontSize=15 -t disableLeaveAlert=true -t screenReaderMode=true \\
  /bin/bash --login
Restart=always
RestartSec=2

[Install]
WantedBy=multi-user.target
EOF
    systemctl daemon-reload
    systemctl enable --now d2dash-ttyd.service
    echo "==> ethernet: link-local fallback so a bare cable to a laptop works"
    for con in $(nmcli -t -f NAME,TYPE con show | awk -F: '$2=="802-3-ethernet"{print $1}'); do
      nmcli con modify "$con" ipv4.method auto ipv4.link-local enabled ipv4.may-fail yes \
        ipv4.dhcp-timeout 10 connection.autoconnect yes 2>/dev/null \
        || echo "note: could not modify '$con' (netplan-managed?)"
    done
    echo "web terminal: http://disco2.local:$PORT/  (user $SERVICE_USER)"
    echo "laptop on a bare cable: plug in, wait ~15 s, same address"
    ;;
  connect)
    echo "==> Raspberry Pi Connect (browser shell from anywhere the Pi has internet)"
    apt-get install -y -q rpi-connect-lite
    loginctl enable-linger "$SERVICE_USER"
    su - "$SERVICE_USER" -c "rpi-connect on && rpi-connect signin"
    echo "open the link above once to pair; then connect.raspberrypi.com → disco2 → Remote shell"
    ;;
  off)
    systemctl disable --now d2dash-ttyd.service 2>/dev/null || true
    echo "web terminal stopped"
    ;;
  *) echo "usage: $0 terminal '<password>' | connect | off"; exit 1 ;;
esac
