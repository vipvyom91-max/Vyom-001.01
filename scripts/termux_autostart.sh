#!/data/data/com.termux/files/usr/bin/bash
# Auto-start PW PCB Manager on phone boot
# Place this file at: ~/.termux/boot/start-pw.sh

sleep 10  # Wait for network
cd ~/Vyom-001.01
source ~/.bashrc 2>/dev/null || true
python run.py >> ~/pw_app.log 2>&1 &
echo "PW PCB Manager started at $(date)" >> ~/pw_app.log
