#!/usr/bin/env bash
# Mantém o servidor (uvicorn) e o túnel público (Cloudflare) de pé.
# Se algum cair, reinicia. O link do túnel rápido pode mudar quando o túnel é reaberto;
# o link atual fica em $LOG_DIR/url.txt.
#
# Uso (a partir da pasta do projeto):
#   nohup bash scripts/keep_alive.sh > /dev/null 2>&1 &
#
# Variáveis opcionais:
#   CLOUDFLARED   caminho do binário cloudflared (padrão: cloudflared no PATH)
#   LOG_DIR       pasta para logs e url.txt (padrão: ./logs)
#   PORT          porta do servidor (padrão: 8000)

set -u
cd "$(dirname "$0")/.." || exit 1

PORT="${PORT:-8000}"
LOG_DIR="${LOG_DIR:-./logs}"
CLOUDFLARED="${CLOUDFLARED:-cloudflared}"
mkdir -p "$LOG_DIR"

log() { echo "$(date '+%Y-%m-%d %H:%M:%S') $*" >> "$LOG_DIR/keep_alive.log"; }

start_server() {
  env -u REMOVER_PASSWORD .venv/bin/uvicorn app:app --host 127.0.0.1 --port "$PORT" \
    >> "$LOG_DIR/server.log" 2>&1 &
  SERVER_PID=$!
  log "servidor iniciado (pid $SERVER_PID)"
}

start_tunnel() {
  : > "$LOG_DIR/tunnel.log"
  "$CLOUDFLARED" tunnel --url "http://127.0.0.1:$PORT" >> "$LOG_DIR/tunnel.log" 2>&1 &
  TUNNEL_PID=$!
  log "túnel iniciado (pid $TUNNEL_PID)"
  for _ in $(seq 1 30); do
    url=$(grep -oE 'https://[a-z0-9-]+\.trycloudflare\.com' "$LOG_DIR/tunnel.log" | head -1)
    if [ -n "$url" ]; then
      echo "$url" > "$LOG_DIR/url.txt"
      log "link público: $url"
      return
    fi
    sleep 2
  done
  log "não consegui ler o link do túnel"
}

start_server
start_tunnel

while true; do
  sleep 20
  if ! kill -0 "$SERVER_PID" 2>/dev/null; then
    log "servidor caiu; reiniciando"
    start_server
  fi
  if ! kill -0 "$TUNNEL_PID" 2>/dev/null || grep -q "Tunnel not found" <(tail -n 5 "$LOG_DIR/tunnel.log"); then
    log "túnel caiu; reiniciando"
    kill "$TUNNEL_PID" 2>/dev/null
    start_tunnel
  fi
done
