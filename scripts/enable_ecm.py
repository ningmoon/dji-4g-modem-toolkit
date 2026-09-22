"""Safely enable QDC507 ECM mode through one fixed, verified workflow."""

import argparse
from pathlib import Path
import re
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from dji4g_toolkit.at_query import validate_ecm_workflow_command
from dji4g_toolkit.ecm_conversion import (
    ConversionError,
    PostWriteVerificationError,
    enable_ecm,
)


def _redact(text: str) -> str:
    return re.sub(r"(?<!\d)(\d{2})\d{8,16}(\d{3})(?!\d)", r"\1***********\2", text)


def _linux_exchange(port: str, command: str) -> str:
    from dji4g_toolkit.linux_serial import exchange

    validate_ecm_workflow_command(command)
    return _redact(exchange(Path(port), command, required_interface="02"))


def _windows_exchange(port: str, command: str, baudrate: int) -> str:
    from dji4g_toolkit.serial_probe import verify_usb_port

    validate_ecm_workflow_command(command)
    verify_usb_port(port, 0x2CA3, 0x4006)
    import serial

    with serial.Serial(
        port, baudrate, bytesize=serial.EIGHTBITS,
        parity=serial.PARITY_NONE, stopbits=serial.STOPBITS_ONE,
        timeout=0.25, write_timeout=1,
    ) as conn:
        conn.dtr = True
        conn.rts = True
        conn.reset_input_buffer()
        conn.write((command + "\r").encode("ascii"))
        deadline = time.monotonic() + 3.0
        response = bytearray()
        while time.monotonic() < deadline and len(response) < 4096:
            response.extend(conn.read(256))
            if re.search(
                rb"(?:^|\r|\n)(?:OK|ERROR|\+CME ERROR:.*|\+CMS ERROR:.*)(?:\r|\n|$)",
                response,
            ):
                break
    return _redact(response.decode("ascii", errors="replace") or "(no response)")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--port", required=True,
        help="Verified COM<number> on Windows or absolute /dev/ttyUSB<number> on Linux/WSL",
    )
    parser.add_argument("--baudrate", type=int, default=115200, help=argparse.SUPPRESS)
    parser.add_argument(
        "--reboot", action="store_true",
        help="After verified read-back, send the one controlled reboot needed to activate ECM",
    )
    parser.add_argument(
        "--yes", action="store_true",
        help="Non-interactive authorization for both ENABLE and REBOOT prompts",
    )
    args = parser.parse_args()

    if sys.platform == "win32":
        exchange = lambda command: _windows_exchange(args.port, command, args.baudrate)
    elif sys.platform.startswith("linux"):
        exchange = lambda command: _linux_exchange(args.port, command)
    else:
        print("Unsupported platform: use Windows or Linux/WSL", file=sys.stderr)
        return 1

    def authorize(action: str) -> bool:
        if args.yes:
            return True
        try:
            answer = input(f"Type {action} to authorize this exact step: ").strip()
        except EOFError:
            return False
        return answer == action

    try:
        result = enable_ecm(exchange, authorize, reboot=args.reboot)
    except PostWriteVerificationError as exc:
        print(f"STOPPED AFTER WRITE: {exc}", file=sys.stderr)
        return 2
    except (ConversionError, OSError, ValueError) as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"FAILED SAFELY: {exc}", file=sys.stderr)
        return 1

    print(f"Verified usbnet={result.after.usbnet}")
    print(f"Verified usbcfg={result.after.usbcfg}")
    print(f"Verified usbid={result.after.usbid}")
    if result.changed:
        print("Changed usbnet: 0 -> 1")
    else:
        print("No setting write was needed; usbnet was already 1")
    if result.rebooted:
        print("Controlled reboot accepted; USB re-enumeration is expected")
    else:
        print("No reboot sent. Rerun with --reboot after verifying stable power")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
