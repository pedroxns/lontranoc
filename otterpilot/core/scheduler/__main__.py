from otterpilot.core.scheduler.bootstrap import (
    build_default_scheduler,
)


def main() -> None:
    scheduler = build_default_scheduler()

    print(
        "OtterPilot Polling Scheduler iniciado.",
        flush=True,
    )

    scheduler.run_forever()


if __name__ == "__main__":
    main()
