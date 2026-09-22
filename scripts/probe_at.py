"""Send one explicitly selected read-only command to a verified USB COM port."""

import argparse
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from dji4g_toolkit.at_query import validate_command
from dji4g_toolkit.serial_probe import verify_usb_port


def redact(text: str) -> str:
    # Do not accidentally copy a whole IMEI/IMSI/ICCID into a tracked file.
    return re.sub(r"(?<!\d)(\d{2})\d{8,16}(\d{3})(?!\d)", r"\1***********\2", text)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", required=True, help="COM port verified as the target modem")
    parser.add_argument("--command", default="AT", help="One exact read-only AT command (default: AT)")
    parser.add_argument("--baudrate", type=int, default=115200)
    args = parser.parse_args()

    try:
        command = validate_command(args.command)
        verify_usb_port(args.port, 0x2CA3, 0x4006)
        import serial

        with serial.Serial(
            args.port, args.baudrate, bytesize=serial.EIGHTBITS,
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
                if re.search(rb"(?:^|\r|\n)(?:OK|ERROR|\+CME ERROR:.*|\+CMS ERROR:.*)(?:\r|\n|$)", response):
                    break
        print(redact(response.decode("ascii", errors="replace")) or "(no response)")
        return 0
    except Exception as exc:
        print(f"No query sent or query failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
