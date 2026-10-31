"""Comandos administrativos: `otterpilot <comando>`."""

from __future__ import annotations

import argparse
import getpass
import os
import secrets
import sys


def _chown_to_service_user(path) -> None:
    # Arquivos criados pelo root precisam continuar legíveis pelo serviço.
    if os.geteuid() != 0:
        return

    try:
        import pwd

        user = pwd.getpwnam("otterpilot")
        os.chown(path, user.pw_uid, user.pw_gid)
    except (KeyError, OSError):
        pass


def cmd_set_password(args: argparse.Namespace) -> int:
    from otterpilot.api import auth

    if args.generate:
        password = secrets.token_urlsafe(12)
    else:
        password = getpass.getpass("Nova senha de administrador: ")

        if password != getpass.getpass("Confirme a senha: "):
            print("As senhas não conferem.", file=sys.stderr)
            return 1

    try:
        auth.set_password(password)
    except ValueError as error:
        print(error, file=sys.stderr)
        return 1

    _chown_to_service_user(auth.AUTH_FILE)

    if args.generate:
        print(f"Senha de administrador: {password}")
    else:
        print("Senha atualizada.")

    return 0


def cmd_status(args: argparse.Namespace) -> int:
    from otterpilot.overview.system import build_overview

    overview = build_overview()
    print(overview["summary"])

    for problem in overview["problems"]:
        print(
            f"  [{problem['impact']}] {problem['connector']}/{problem['capability']} "
            f"{problem['resource_id']}: {problem['reason']}"
        )

    return 0 if overview["overall_status"] == "healthy" else 2


def cmd_forget(args: argparse.Namespace) -> int:
    from otterpilot.state import build_default_state_store

    removed = build_default_state_store().delete(
        connector=args.connector,
        capability=args.capability,
        resource_id=args.resource_id,
    )

    print("Removido." if removed else "Recurso não encontrado.")
    return 0 if removed else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="otterpilot")
    commands = parser.add_subparsers(dest="command", required=True)

    password = commands.add_parser("set-password", help="Define a senha de administrador da interface")
    password.add_argument("--generate", action="store_true", help="Gera e imprime uma senha aleatória")
    password.set_defaults(handler=cmd_set_password)

    status = commands.add_parser("status", help="Resumo do estado atual")
    status.set_defaults(handler=cmd_status)

    forget = commands.add_parser("forget", help="Remove um recurso do estado atual")
    forget.add_argument("connector")
    forget.add_argument("capability")
    forget.add_argument("resource_id")
    forget.set_defaults(handler=cmd_forget)

    args = parser.parse_args(argv)
    return args.handler(args)


if __name__ == "__main__":
    sys.exit(main())
