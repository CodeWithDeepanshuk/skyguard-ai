#!/usr/bin/env bash
# ==============================================================================
# SkyGuard AI — Oracle Cloud VM Setup Script (SIH 26073)
# Configures Oracle Always Free VM as the Fixed-IP Gateway for IMD AWS API
# ==============================================================================
set -euo pipefail

echo "======================================================================"
echo "  SkyGuard AI — Oracle Cloud Always Free Gateway Installer"
echo "  Problem Statement: SIH 26073 | India Meteorological Department"
echo "======================================================================"

if [[ $EUID -ne 0 ]]; then
   echo "[-] Please run as root or with sudo: sudo bash setup_oracle_vm.sh"
   exit 1
fi

INSTALL_DIR="/opt/skyguard-gateway"
echo "[1] Creating gateway directory: ${INSTALL_DIR}..."
mkdir -p "${INSTALL_DIR}/raw_archives"

# Detect OS & ensure Python 3 is installed
echo "[2] Checking Python 3 installation..."
if command -v apt-get &>/dev/null; then
    apt-get update -qq
    apt-get install -y -qq python3 curl
elif command -v dnf &>/dev/null; then
    dnf install -y -q python3 curl
elif command -v yum &>/dev/null; then
    yum install -y -q python3 curl
fi

PYTHON_BIN="$(which python3)"
echo "    Found Python at: ${PYTHON_BIN} ($(${PYTHON_BIN} --version))"

# Copy or create collector script
SCRIPT_SRC="$(dirname "$0")/collector.py"
if [[ -f "${SCRIPT_SRC}" ]]; then
    cp "${SCRIPT_SRC}" "${INSTALL_DIR}/collector.py"
else
    echo "[-] collector.py not found next to setup script. Please place collector.py in the same directory."
    exit 1
fi
chmod 755 "${INSTALL_DIR}/collector.py"

# Environment file setup
if [[ ! -f "${INSTALL_DIR}/.env" ]]; then
    ENV_SRC="$(dirname "$0")/.env.example"
    if [[ -f "${ENV_SRC}" ]]; then
        cp "${ENV_SRC}" "${INSTALL_DIR}/.env"
    else
        touch "${INSTALL_DIR}/.env"
    fi
    chmod 600 "${INSTALL_DIR}/.env"
    echo "[!] Created ${INSTALL_DIR}/.env template with secure 0600 permissions."
    echo "    IMPORTANT: Edit ${INSTALL_DIR}/.env with your real IMD credentials & Render URL!"
fi

# Detect Current Egress IP
echo "[3] Checking Public IPv4 of this VM..."
CURRENT_IP="$(${PYTHON_BIN} "${INSTALL_DIR}/collector.py" --check-ip | grep 'Public Egress IP:' | awk '{print $NF}' || true)"
echo "    >>> YOUR ORACLE VM RESERVED PUBLIC IP IS: ${CURRENT_IP} <<<"
echo "    * Note: Register this exact IPv4 in the IMD Portal (api.imd.gov.in) when creating your X-API-KEY."

# Configure Systemd Service
echo "[4] Installing systemd service: skyguard-collector.service..."
cat <<EOF > /etc/systemd/system/skyguard-collector.service
[Unit]
Description=SkyGuard AI Official IMD AWS Collector
After=network-online.target
Wants=network-online.target

[Service]
Type=oneshot
User=root
WorkingDirectory=${INSTALL_DIR}
EnvironmentFile=${INSTALL_DIR}/.env
ExecStart=${PYTHON_BIN} ${INSTALL_DIR}/collector.py --once
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

# Configure Systemd Timer (runs every 15 minutes)
echo "[5] Installing systemd timer: skyguard-collector.timer (15-min cadence)..."
cat <<EOF > /etc/systemd/system/skyguard-collector.timer
[Unit]
Description=Trigger SkyGuard IMD Collector Every 15 Minutes
Requires=skyguard-collector.service

[Timer]
Unit=skyguard-collector.service
OnCalendar=*:0/15
RandomizedDelaySec=30
Persistent=true

[Install]
WantedBy=timers.target
EOF

# Reload and enable
systemctl daemon-reload
systemctl enable --now skyguard-collector.timer

echo "======================================================================"
echo "  [SUCCESS] Oracle Cloud Gateway Installed & Armed!"
echo "======================================================================"
echo "Next Steps:"
echo "1. Edit configuration with your credentials:"
echo "   sudo nano ${INSTALL_DIR}/.env"
echo ""
echo "2. Test immediate execution:"
echo "   sudo systemctl start skyguard-collector.service"
echo ""
echo "3. View live logs:"
echo "   sudo journalctl -u skyguard-collector.service -f"
echo ""
echo "4. Check timer schedule:"
echo "   sudo systemctl list-timers skyguard-collector.timer"
echo "======================================================================"
