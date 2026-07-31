"""Legacy launcher for the OtterPilot Assistant.

Temporary compatibility entrypoint for the existing systemd service.
"""

from otterpilot.copilot.assistant import main


if __name__ == "__main__":
    main()
