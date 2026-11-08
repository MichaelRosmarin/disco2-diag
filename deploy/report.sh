#!/bin/bash
# One-shot health and diagnostic report: Pi state, K-line adapter, network, then faults and
# every live input from the Td5 and the SLABS (switches to SLABS for ~15 s, then back).
#   bash deploy/report.sh            → prints and saves ~/report-<date>.txt
OUT=~/report-$(date +%Y%m%d-%H%M%S).txt; exec > >(tee "$OUT") 2>&1
snap() { curl -s localhost/api/snapshot | python3 -c "
import sys,json; s=json.load(sys.stdin); g=s.get('signals',{})
print('ECU',s['module'],'|',s['status'],'| error:',s.get('error'),'| polls:',s.get('polls'),'| errors:',s.get('errors'))
print('FAULTS:', s.get('faults') or 'none')
for k,v in sorted(g.items()): print(f'  {k:24s} {str(v.get(\"v\")):>10s} {v.get(\"u\") or \"\":8s} {v.get(\"c\") or \"\"}')
sens=s.get('sensors') or {}; st=sens.get('status','none'); print('sensor board:', 'not fitted' if st in ('error','none') else st)"; }
switch() { curl -s -X POST -H 'Content-Type: application/json' -d "{\"module\":\"$1\"}" localhost/api/module >/dev/null
  for i in $(seq 1 30); do sleep 1; curl -s localhost/api/snapshot | grep -q "\"status\": *\"connected\"" && break; done; sleep 3; }
echo "=== DISCO2 REPORT $(date) ==="
echo "--- Pi ---"; uptime; vcgencmd measure_temp; vcgencmd get_throttled; echo "(0x0 = no under-voltage or throttling ever)"
echo "--- services ---"; systemctl is-active d2dash d2dash-ttyd d2dash-eth 2>&1 | paste - - -
echo "--- K-line adapter ---"; ls -l /dev/kline 2>&1; lsusb | grep -i -E "ftdi|future|0403" || echo "NO FTDI ADAPTER SEEN"
echo "--- network ---"; ip -br addr | grep -v "^lo"; nmcli -t -f NAME,DEVICE con show --active
echo "--- ethernet link drops this boot ---"; dmesg | grep -c "eth0: Link is Down"; ethtool eth0 2>/dev/null | grep -E "Speed|Link det"
echo "--- storage ---"; df -h / /var/lib/d2dash 2>/dev/null | tail -n +2; ls -lt /var/lib/d2dash/logs | head -n 6
echo "--- dashboard errors (this boot) ---"; journalctl -u d2dash -b --no-pager | grep -i -E "error|warn|traceback|exception" | tail -n 15 || true
echo "--- version ---"; (cd ~/disco2-diag 2>/dev/null && git log --oneline -1)
echo; echo "=== ENGINE (Td5) ==="; switch td5; snap
echo; echo "=== SLABS (ABS lights will come on for ~15 s) ==="; switch slabs; snap
switch td5; echo "engine reconnect after SLABS: $(curl -s localhost/api/snapshot | python3 -c 'import sys,json; print(json.load(sys.stdin)["status"])')"
echo; echo "=== back on engine. saved to $OUT ==="
