"""Linux ttyUSB identity validation and bounded AT exchange."""

import fcntl
import os
from pathlib import Path
import re
import select
import stat
import struct
import termios
import time


TARGET_VID = "2ca3"
TARGET_PID = "4006"


def usb_identity(port: Path) -> tuple[str, str, str]:
    if not re.fullmatch(r"ttyUSB[0-9]+", port.name) or port.parent != Path("/dev"):
        raise ValueError("Only an absolute /dev/ttyUSB<number> path is accepted")
    if not stat.S_ISCHR(port.stat().st_mode):
        raise ValueError("Port is not a character device")
    device = (Path("/sys/class/tty") / port.name / "device").resolve(strict=True)
    interface = next((p for p in (device, *device.parents) if (p / "bInterfaceNumber").is_file()), None)
    if interface is None:
        raise ValueError("Cannot establish the USB interface from sysfs")
    parent = next((p for p in (interface, *interface.parents)
                   if (p / "idVendor").is_file() and (p / "idProduct").is_file()), None)
    if parent is None:
        raise ValueError("Cannot establish USB VID/PID from sysfs")
    vid = (parent / "idVendor").read_text().strip().lower()
    pid = (parent / "idProduct").read_text().strip().lower()
    number = (interface / "bInterfaceNumber").read_text().strip().lower()
    if (vid, pid) != (TARGET_VID, TARGET_PID):
        raise ValueError("Refused: ttyUSB does not belong to DJI 2ca3:4006")
    return vid, pid, number


def exchange(port: Path, command: str, *, required_interface: str | None = None) -> str:
    vid, pid, interface = usb_identity(port)
    if required_interface is not None and interface.casefold() != required_interface.casefold():
        raise ValueError(
            f"Refused: expected USB interface {required_interface}, observed {interface}"
        )
    fd = os.open(port, os.O_RDWR | os.O_NOCTTY | os.O_NONBLOCK)
    try:
        old = termios.tcgetattr(fd)
        try:
            settings = termios.tcgetattr(fd)
            settings[0] = 0
            settings[1] = 0
            settings[2] = (
                settings[2] & ~(termios.CSIZE | termios.PARENB | termios.CSTOPB)
            ) | termios.CS8 | termios.CREAD | termios.CLOCAL
            settings[3] = 0
            settings[4] = termios.B115200
            settings[5] = termios.B115200
            termios.tcsetattr(fd, termios.TCSANOW, settings)
            fcntl.ioctl(
                fd, termios.TIOCMBIS,
                struct.pack("I", termios.TIOCM_DTR | termios.TIOCM_RTS),
            )
            termios.tcflush(fd, termios.TCIFLUSH)
            os.write(fd, (command + "\r").encode("ascii"))
            deadline = time.monotonic() + 3.0
            response = bytearray()
            while time.monotonic() < deadline and len(response) < 4096:
                ready, _, _ = select.select([fd], [], [], max(0, deadline - time.monotonic()))
                if not ready:
                    break
                try:
                    response.extend(os.read(fd, 256))
                except BlockingIOError:
                    continue
                if re.search(
                    rb"(?:^|\r|\n)(?:OK|ERROR|\+CME ERROR:.*|\+CMS ERROR:.*)(?:\r|\n|$)",
                    response,
                ):
                    break
            return response.decode("ascii", errors="replace") or "(no response)"
        finally:
            try:
                termios.tcsetattr(fd, termios.TCSANOW, old)
            except OSError:
                # A successful usbnet write or modem reboot may remove the tty
                # before its original host settings can be restored. Closing the
                # dead descriptor is sufficient; do not hide an already received
                # modem response with this host-side cleanup error.
                pass
    finally:
        os.close(fd)
