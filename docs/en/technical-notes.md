[中文](../technical-notes.md) | [English](technical-notes.md)

# Technical notes and validation boundaries

## Why only `usbnet` is changed

The test module originally used `usbnet=0`, a USB network protocol that Apple devices did not use directly. After changing it to `usbnet=1`, the module exposed standard CDC-ECM control and data interfaces, allowing an iPhone or iPad to recognize it as a USB Ethernet device.

The only persistent change was:

```text
AT+QCFG="usbnet",1
```

One `AT+CFUN=1,1` controlled reboot then caused the USB composition to re-enumerate. The procedure did not modify `usbcfg`, `usbid`, the VID/PID, APN, SIM/eSIM configuration, or firmware.

## Verified baseline

| Item | Value |
|---|---|
| Product | Baiwang QDC507 |
| Revision | `QDC507GLEFM21` |
| Firmware | `QDC507GLEFM21_01.001.02.004` |
| VID:PID | `2CA3:4006` |
| AT function | USB interface `02` |
| Original `usbnet` | `0` |
| Current `usbnet` | `1` |
| `usbcfg` | `0x2CA3,0x4006,1,1,1,1,1,0,0` (unchanged) |
| `usbid` | `11427,16390` (unchanged) |

## Validation results

| Platform | Status | Evidence |
|---|---|---|
| iPhone / iOS | PASS | Direct USB Ethernet recognition and Internet access were verified. The exact iOS version was not recorded. |
| iPad / iPadOS | PASS | Direct USB Ethernet recognition and Internet access were verified. The exact iPadOS version was not recorded. |
| Linux / WSL2 | PASS | ECM obtained a DHCP address, and both the module gateway and public IPv4 connectivity were verified. |
| Native Windows 10 | BLOCKED | USB enumeration succeeded, but no matching native ECM network adapter was available. |
| macOS | NOT TESTED | No physical test has been recorded. |

## Physical validation of the conversion tool

`scripts/enable_ecm.py` has been tested against the physical module described above. It correctly identified `2CA3:4006` / interface `02`, read and validated the full baseline, remained idempotent without repeating the write when `usbnet=1`, and completed one controlled reboot. After reboot, the VID/PID, `usbnet`, `usbcfg`, and `usbid` all retained their expected values.

That module had already undergone the controlled `usbnet=0 → 1` procedure manually, so it was not rolled back merely to replay the write during the script test. The script's physical-device identification, read, and reboot paths have been verified. Its `AT+QCFG="usbnet",1` write branch is covered by offline automated tests but has not yet been run on a second physical module that remains at `usbnet=0`.

## Safety boundaries

- A second module with the same appearance must still have its own model, firmware, and configuration baseline read before any write.
- `2CA3:4006` is a necessary condition, not sufficient proof that a serial port is the target AT port.
- Do not change the VID/PID, `usbcfg`, or `usbid`, or install an untrusted driver, to work around a host compatibility problem.
- The Apple tests establish compatibility for the test module only, not every device, OS, carrier, cable, or power arrangement.
- WSL USB bindings, network interfaces, DHCP addresses, and routes are temporary host state and do not travel with the module.

## Privacy

An IMEI, IMSI, ICCID, phone number, APN credential, or eSIM detail is not required to reproduce this work and should never be included in an issue, log, or commit.
