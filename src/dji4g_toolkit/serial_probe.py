"""Verify the Windows COM -> PnP -> hardware-ID chain before opening a port."""

import json
import re
import subprocess
import sys


def verify_usb_port(port: str, expected_vid: int, expected_pid: int) -> None:
    if sys.platform != "win32" or not re.fullmatch(r"COM[1-9][0-9]*", port, re.I):
        raise ValueError("Only a Windows COM port is supported for this bring-up")
    from serial.tools import list_ports

    matches = [item for item in list_ports.comports() if item.device.casefold() == port.casefold()]
    if len(matches) != 1:
        raise ValueError("Port is absent or ambiguous in serial enumeration")
    item = matches[0]
    if item.vid != expected_vid or item.pid != expected_pid:
        raise ValueError(
            f"Refused: {port} does not enumerate as USB VID:PID "
            f"{expected_vid:04X}:{expected_pid:04X} (observed "
            f"{item.vid!s}:{item.pid!s})"
        )

    # The display name identifies the port; instance and hardware IDs prove
    # ownership. An unrelated Quectel or Bluetooth serial port is refused.
    ps = r'''
$ErrorActionPreference = 'Stop'
$port = 'PORT_PLACEHOLDER'
$portDevices = @(Get-PnpDevice -PresentOnly -Class Ports | Where-Object {
    $_.FriendlyName -match ('\(' + [regex]::Escape($port) + '\)$')
})
$portDevices | ForEach-Object {
    $ids = @(Get-PnpDeviceProperty -InstanceId $_.InstanceId -KeyName 'DEVPKEY_Device_HardwareIds' -ErrorAction Stop).Data
    [pscustomobject]@{ InstanceId = $_.InstanceId; HardwareIds = $ids }
} | ConvertTo-Json -Compress
'''.replace("PORT_PLACEHOLDER", port.upper())
    result = subprocess.run(
        ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", ps],
        capture_output=True, text=True, timeout=10, check=True,
    )
    records = json.loads(result.stdout) if result.stdout.strip() else []
    if records is None:
        records = []
    if isinstance(records, dict):
        records = [records]
    prefix = f"USB\\VID_{expected_vid:04X}&PID_{expected_pid:04X}&MI_02"
    if len(records) != 1 or not records[0]["InstanceId"].upper().startswith(prefix):
        raise ValueError("Refused: COM port PnP instance is not target MI_02")
    ids = records[0]["HardwareIds"]
    if isinstance(ids, str):
        ids = [ids]
    if not any(identifier.upper().startswith(prefix) for identifier in ids):
        raise ValueError("Refused: COM port hardware IDs do not identify target MI_02")
