"""List target ttyUSB interfaces or send one allowlisted AT query on Linux."""

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from dji4g_toolkit.at_query import validate_command
from dji4g_toolkit.linux_serial import exchange, usb_identity


def redact(response: str) -> str:
    return re.sub(r"(?<!\d)(\d{2})\d{8,16}(\d{3})(?!\d)", r"\1***********\2", response)


def query(port: Path, command: str) -> str:
    validate_command(command)
    vid, pid, interface = usb_identity(port)
    print(f"Verified {port}: {vid}:{pid} interface {interface}", file=sys.stderr)
    return redact(exchange(port, command))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--list", action="store_true", help="List only ttyUSB ports belonging to 2ca3:4006")
    mode.add_argument("--port", type=Path, help="One verified /dev/ttyUSB<number> port")
    parser.add_argument("--command", default="AT", help="One exact read-only command (default: AT)")
    args = parser.parse_args()
    try:
        if args.list:
            for port in sorted(Path("/dev").glob("ttyUSB[0-9]*")):
                try:
                    vid, pid, interface = usb_identity(port)
                    print(f"{port} -> {vid}:{pid} -> interface {interface}")
                except (OSError, ValueError):
                    continue
        else:
            print(query(args.port, args.command))
        return 0
    except (OSError, ValueError) as exc:
        print(f"No query sent or query failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
