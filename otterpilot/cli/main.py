"""Comandos administrativos: `otterpilot <comando>`."""

from __future__ import annotations

import argparse
import getpass
import os
import secrets
import sys


def _chown_to_service_user(path) -> None:
    # Arquivos criados pelo root precisam continuar legíveis pelo serviço.
    if not hasattr(os, "geteuid") or os.geteuid() != 0:  # sem geteuid (Windows) ou sem ser root: nada a fazer
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


def cmd_token_create(args: argparse.Namespace) -> int:
    from otterpilot.api import auth

    try:
        token = auth.create_service_token(args.name, args.scope or [auth.SCOPE_COPILOT_VOICE])
    except ValueError as error:
        print(error, file=sys.stderr)
        return 1

    _chown_to_service_user(auth.AUTH_FILE)
    print(f"Token '{args.name}' criado. Guarde agora: ele não será mostrado de novo.")
    print(token)
    return 0


def cmd_token_list(args: argparse.Namespace) -> int:
    from otterpilot.api import auth

    tokens = auth.list_service_tokens()

    if not tokens:
        print("Nenhum token de serviço.")

    for item in tokens:
        print(f"{item['name']}\t{','.join(item['scopes'])}\t{item['created']}")

    return 0


def cmd_token_revoke(args: argparse.Namespace) -> int:
    from otterpilot.api import auth

    removed = auth.revoke_service_token(args.name)

    if removed:
        # A gravação substitui o arquivo: rodando como root, ele ficaria do root e
        # a API (usuário otterpilot) perderia a leitura do auth.json.
        _chown_to_service_user(auth.AUTH_FILE)

    print("Revogado." if removed else "Token não encontrado.")
    return 0 if removed else 1


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

    token = commands.add_parser("token", help="Tokens de serviço (máquinas que usam a API)")
    token_commands = token.add_subparsers(dest="token_command", required=True)

    token_create = token_commands.add_parser("create", help="Cria um token (mostrado uma única vez)")
    token_create.add_argument("name")
    token_create.add_argument("--scope", action="append", help="Escopo (padrão: copilot:voice); repetível")
    token_create.set_defaults(handler=cmd_token_create)

    token_list = token_commands.add_parser("list", help="Lista os tokens (sem o valor)")
    token_list.set_defaults(handler=cmd_token_list)

    token_revoke = token_commands.add_parser("revoke", help="Revoga um token")
    token_revoke.add_argument("name")
    token_revoke.set_defaults(handler=cmd_token_revoke)

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
