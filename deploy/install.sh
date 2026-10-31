#!/usr/bin/env bash
# Instala ou atualiza o OtterPilot neste host (Debian + systemd).
#
#   sudo deploy/install.sh
#
# Idempotente: nunca sobrescreve /etc/otterpilot/.env, os YAML em
# /etc/otterpilot/config nem as credenciais. Não habilita nem inicia units.
set -euo pipefail

SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PREFIX=/opt/otterpilot
ETC=/etc/otterpilot
STATE=/var/lib/otterpilot
SERVICE_USER=otterpilot

if [[ $EUID -ne 0 ]]; then
  echo "Execute como root." >&2
  exit 1
fi

if ! id "$SERVICE_USER" &>/dev/null; then
  useradd --system --home-dir "$STATE" --no-create-home \
    --shell /usr/sbin/nologin "$SERVICE_USER"
fi

install -d -m 0750 -o "$SERVICE_USER" -g "$SERVICE_USER" "$STATE"

if [[ ! -x "$PREFIX/venv/bin/python" ]]; then
  install -d -m 0755 "$PREFIX"
  python3 -m venv "$PREFIX/venv"
fi
"$PREFIX/venv/bin/pip" install --quiet --upgrade pip
"$PREFIX/venv/bin/pip" install --quiet --upgrade "$SRC"
# O setuptools deixa artefatos de build (como root) dentro do checkout.
rm -rf "$SRC/build" "$SRC"/*.egg-info

install -d -m 0755 "$ETC" "$ETC/config"
install -d -m 0700 "$ETC/credentials"

for file in "$SRC"/config/*.yaml; do
  target="$ETC/config/$(basename "$file")"
  [[ -e "$target" ]] || install -m 0644 "$file" "$target"
done

if [[ ! -e "$ETC/.env" ]]; then
  install -m 0640 -g "$SERVICE_USER" "$SRC/deploy/otterpilot.env.example" "$ETC/.env"
fi

install -m 0644 "$SRC"/deploy/systemd/otterpilot-*.service /etc/systemd/system/
systemctl daemon-reload

echo "OtterPilot instalado em $PREFIX ($("$PREFIX/venv/bin/python" -c 'import otterpilot; print(otterpilot.__version__)'))."
echo "Configure $ETC/.env e $ETC/config/, depois:"
echo "  systemctl enable --now otterpilot-scheduler otterpilot-zigbee2mqtt otterpilot-frigate otterpilot-copilot"
