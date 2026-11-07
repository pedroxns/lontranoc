from __future__ import annotations

import uvicorn

from otterpilot.core.config import get_env, get_int


def main() -> None:
    uvicorn.run(
        "otterpilot.api.app:app",
        host=get_env("OTTERPILOT_API_HOST", "0.0.0.0") or "0.0.0.0",
        port=get_int("OTTERPILOT_API_PORT", 8470),
        access_log=False,
        proxy_headers=True,
        forwarded_allow_ips=get_env("OTTERPILOT_TRUSTED_PROXIES", "127.0.0.1"),
    )


if __name__ == "__main__":
    main()
