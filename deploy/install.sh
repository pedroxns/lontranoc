#!/usr/bin/env bash
# Instala ou atualiza o OtterPilot neste host (Debian/Ubuntu com systemd).
#
#   sudo deploy/install.sh            instala/atualiza e (re)inicia os serviços
#   sudo deploy/install.sh --no-start instala/atualiza sem mexer nos serviços
#
# Idempotente: nunca sobrescreve /etc/otterpilot/.env, os YAML em
# /etc/otterpilot/config, as credenciais nem a senha da interface.
set -euo pipefail

SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PREFIX=/opt/otterpilot
ETC=/etc/otterpilot
STATE=/var/lib/otterpilot
SERVICE_USER=otterpilot
UNITS=(otterpilot-scheduler otterpilot-zigbee2mqtt otterpilot-frigate otterpilot-copilot otterpilot-api)
CREDENTIALS=(proxmox_token_id proxmox_token_secret)

START=1
[[ "${1:-}" == "--no-start" ]] && START=0

if [[ $EUID -ne 0 ]]; then
  echo "Execute como root." >&2
  exit 1
fi

if ! command -v python3 >/dev/null || ! python3 -c 'import sys, venv; sys.exit(sys.version_info < (3, 11))' 2>/dev/null; then
  echo "É necessário Python 3.11+ com o módulo venv (apt install python3-venv)." >&2
  exit 1
fi

# ---- usuário e diretórios

if ! id "$SERVICE_USER" &>/dev/null; then
  useradd --system --home-dir "$STATE" --no-create-home \
    --shell /usr/sbin/nologin "$SERVICE_USER"
fi

install -d -m 0750 -o "$SERVICE_USER" -g "$SERVICE_USER" "$STATE"

# A API grava a configuração editada na interface.
install -d -m 0770 -o root -g "$SERVICE_USER" "$ETC"
install -d -m 0750 -o "$SERVICE_USER" -g "$SERVICE_USER" "$ETC/config"
install -d -m 0700 -o root -g root "$ETC/credentials"

# ---- código

if [[ ! -x "$PREFIX/venv/bin/python" ]]; then
  install -d -m 0755 "$PREFIX"
  python3 -m venv "$PREFIX/venv"
fi
"$PREFIX/venv/bin/pip" install --quiet --upgrade pip
"$PREFIX/venv/bin/pip" install --quiet --upgrade "$SRC"
# O setuptools deixa artefatos de build (como root) dentro do checkout.
rm -rf "$SRC/build" "$SRC"/*.egg-info
cat > /usr/local/bin/otterpilot <<WRAPPER
#!/bin/sh
OTTERPILOT_ROOT="\${OTTERPILOT_ROOT:-$ETC}" exec "$PREFIX/venv/bin/otterpilot" "\$@"
WRAPPER
chmod 0755 /usr/local/bin/otterpilot

# ---- configuração

if [[ ! -e "$ETC/.env" ]]; then
  install -m 0600 -o "$SERVICE_USER" -g "$SERVICE_USER" \
    "$SRC/deploy/otterpilot.env.example" "$ETC/.env"
else
  chown "$SERVICE_USER:$SERVICE_USER" "$ETC/.env"
  chmod 0600 "$ETC/.env"
fi

find "$ETC/config" -maxdepth 1 -name '*.yaml' -exec chown "$SERVICE_USER:$SERVICE_USER" {} + -exec chmod 0640 {} +

# Credenciais systemd são opcionais; vazias, o valor vem da interface/.env.
# Os arquivos precisam existir porque LoadCredential= falha sem eles.
for name in "${CREDENTIALS[@]}"; do
  [[ -e "$ETC/credentials/$name" ]] || install -m 0600 -o root -g root /dev/null "$ETC/credentials/$name"
done

GENERATED_PASSWORD=""
if [[ ! -s "$ETC/auth.json" ]]; then
  GENERATED_PASSWORD="$(/usr/local/bin/otterpilot set-password --generate | sed 's/^.*: //')"
fi
chown "$SERVICE_USER:$SERVICE_USER" "$ETC/auth.json"
chmod 0600 "$ETC/auth.json"

# ---- serviços

install -m 0644 "$SRC"/deploy/systemd/otterpilot-*.service /etc/systemd/system/
systemctl daemon-reload

if [[ $START -eq 1 ]]; then
  systemctl enable --quiet "${UNITS[@]}"
  systemctl restart "${UNITS[@]}"
fi

VERSION="$("$PREFIX/venv/bin/python" -c 'import otterpilot; print(otterpilot.__version__)')"
PORT="$(grep -E '^OTTERPILOT_API_PORT=' "$ETC/.env" | cut -d= -f2 || true)"
HOST_IP="$(hostname -I 2>/dev/null | awk '{print $1}')"

echo
echo "OtterPilot $VERSION instalado."
echo "Interface: http://${HOST_IP:-<host>}:${PORT:-8470}/"

if [[ -n "$GENERATED_PASSWORD" ]]; then
  echo "Senha inicial de administrador: $GENERATED_PASSWORD"
  echo "(troque em Configurações > Sistema, ou com: sudo otterpilot set-password)"
fi

if [[ $START -eq 0 ]]; then
  echo "Serviços não reiniciados (--no-start)."
fi
