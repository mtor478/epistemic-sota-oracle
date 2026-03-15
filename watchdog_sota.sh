#!/bin/bash
WORKSPACE="$HOME/epistemic_client_workspace"
VENV_PYTHON="$WORKSPACE/.venv/bin/python"
LOG_FILE="$WORKSPACE/watchdog_audit.log"

# 1. Auditoria do Daemon de Markov (Agente)
if ! pgrep -f "autopoietic_daemon.py" > /dev/null; then
    echo "$(date) | 🔴 [CRITICAL] Daemon SDE aniquilado. Injetando Ressurreição O(1)..." >> $LOG_FILE
    nohup $VENV_PYTHON "$WORKSPACE/autopoietic_daemon.py" > "$WORKSPACE/daemon.log" 2>&1 &
fi

# 2. Auditoria da Ponte Parasítica (Nó Mestre & Túnel)
if ! pgrep -f "cloudflared tunnel" > /dev/null || ! pgrep -f "epistemic_miner_master:app" > /dev/null; then
    echo "$(date) | 🟡 [WARNING] Colapso L4 detectado no Oráculo. Acionando sota_resurrection.sh..." >> $LOG_FILE
    bash "$WORKSPACE/sota_resurrection.sh" >> "$WORKSPACE/resurrection_cron.log" 2>&1
fi
