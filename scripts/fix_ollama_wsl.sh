#!/bin/bash
echo "[*] Configuring Ollama for External Access (0.0.0.0)..."
mkdir -p /etc/systemd/system/ollama.service.d
echo '[Service]' > /etc/systemd/system/ollama.service.d/override.conf
echo 'Environment="OLLAMA_HOST=0.0.0.0"' >> /etc/systemd/system/ollama.service.d/override.conf
echo "[*] Reloading Systemd..."
systemctl daemon-reload
echo "[*] Restarting Ollama..."
systemctl restart ollama
echo "[+] SUCCESS: Ollama is now listening on 0.0.0.0"
