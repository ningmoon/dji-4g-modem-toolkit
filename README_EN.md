[简体中文](README.md) | [English](README_EN.md)

# DJI 4G Modem iPhone / iPad ECM Toolkit

First-generation DJI 4G modules have recently become popular again. They are interesting devices to experiment with, although used-market prices have risen enough that they may not offer particularly good value.

![First-generation DJI 4G module](docs/assets/model-pic%20%285%29.jpg)

![SIM slot on the first-generation DJI 4G module](docs/assets/model-pic%20%284%29%20.jpg)

This project does not implement or depend on VoHive. Its sole purpose is to switch the USB network mode of a first-generation DJI 4G module (Baiwang QDC507) from `usbnet=0` to `usbnet=1` (CDC-ECM), allowing the module to work as a USB cellular network adapter for an iPhone or iPad with minimal changes.

<img src="docs/assets/model-pic%20%281%29.jpg" alt="DJI 4G module connected to an iPad" width="720">

The project changes exactly one persistent setting: `usbnet`. It does not flash firmware or modify the VID/PID, `usbcfg`, `usbid`, APN, or SIM/eSIM configuration.

## Verified scope

Test device:

- Product: Baiwang QDC507 (first-generation DJI 4G module)
- Firmware: `QDC507GLEFM21_01.001.02.004`
- USB VID:PID: `2CA3:4006`
- Original mode: `usbnet=0`
- Target mode: `usbnet=1` (ECM)

Validation results:

| Platform | Result |
|---|---|
| iPhone | Internet access verified on a physical device |
| iPad | Internet access verified on a physical device |
| Linux / WSL2 | ECM, DHCP, and public IPv4 connectivity verified |
| Native Windows 10 networking | Not available; no matching native ECM driver |
| macOS | Not tested |

Testing covers one module and one set of hardware and software conditions. It does not guarantee compatibility with every module, OS version, carrier, cable, or power arrangement.

## Requirements

- Python 3.10 or later.
- The Linux / WSL2 path uses only the Python standard library and requires no additional Python packages.
- The Windows COM-port path requires `pyserial`:

```powershell
python -m pip install pyserial
```

If Windows does not expose a usable AT serial port, you will also need WSL2, Ubuntu, and `usbipd-win`. See [Windows / WSL2 setup](docs/en/windows-wsl-setup.md) for the complete preparation procedure. Run all repository commands from the repository root.

## Before you begin

`usbnet` is stored persistently by the modem. Before writing anything, verify that:

1. The device enumerates exactly as `2CA3:4006` and is the intended DJI 4G module.
2. The AT port belongs to USB interface `02` of that device. Never guess from a `/dev/ttyUSB*` or `COM*` number.
3. You have read and saved `ATI`, firmware, `usbnet`, `usbcfg`, and `usbid`.
4. Power will remain stable during the write and reboot.

If Windows does not provide a usable AT serial port, follow [Windows / WSL2 setup](docs/en/windows-wsl-setup.md) to attach the module temporarily to Ubuntu.

## Quick procedure

### 1. Verify the device and AT port

On Linux / WSL2, use the repository's read-only probe:

```bash
sudo python3 scripts/probe_at_linux.py --list
sudo python3 scripts/probe_at_linux.py --port /dev/ttyUSB2 --command AT
sudo python3 scripts/probe_at_linux.py --port /dev/ttyUSB2 --command ATI
sudo python3 scripts/probe_at_linux.py --port /dev/ttyUSB2 --command AT+QGMR
sudo python3 scripts/probe_at_linux.py --port /dev/ttyUSB2 --command 'AT+QCFG="usbnet"'
sudo python3 scripts/probe_at_linux.py --port /dev/ttyUSB2 --command 'AT+QCFG="usbcfg"'
sudo python3 scripts/probe_at_linux.py --port /dev/ttyUSB2 --command 'AT+QCFG="usbid"'
```

`/dev/ttyUSB2` was the mapping on the test device only. Always use the script and the actual sysfs mapping. On Windows, run `scripts/detect_device.ps1` for read-only enumeration, then use `scripts/probe_at.py` with the verified COM port.

The expected baseline for the tested module is:

```text
usbnet=0
usbcfg=0x2CA3,0x4006,1,1,1,1,1,0,0
usbid=11427,16390
```

If the model, firmware, or any baseline value differs, stop. Do not copy the write procedure to that device.

### 2. Run the dedicated conversion tool

The conversion tool implements only the fixed, validated `usbnet=0 → 1` workflow. It does not accept arbitrary AT commands. After verifying the port, run:

```bash
sudo python3 scripts/enable_ecm.py --port /dev/ttyUSB2 --reboot
```

If Windows exposes a verified target COM port and `pyserial` is installed, run:

```powershell
python scripts/enable_ecm.py --port COM7 --reboot
```

The tool will:

1. Re-verify the VID:PID and AT interface `02`.
2. Check the model, firmware, `usbnet`, `usbcfg`, and `usbid` baseline.
3. Require the exact confirmation `ENABLE`, then send `AT+QCFG="usbnet",1` once.
4. Read the configuration back immediately and verify that `usbnet=1` while the other two values remain unchanged.
5. Require the exact confirmation `REBOOT` before sending one `AT+CFUN=1,1` controlled reboot.

If the USB device re-enumerates immediately after the write, the tool stops without sending the reboot. Reattach the device, restore the verified AT port, and run the same command again. The tool will recognize the existing `usbnet=1`, re-check the baseline, and perform only the authorized reboot.

Automation may add `--yes` to skip both text confirmations. This never skips device or configuration validation.

### 3. Connect the module to an iPhone or iPad

After the module re-enumerates, connect it to the iPhone or iPad using a USB cable that supports data. The OS should recognize it as a USB Ethernet device and obtain network configuration from the module.

<img src="docs/assets/model-pic%20%282%29.jpg" alt="iPad recognizing the Baiwang Ethernet device" width="720">

A successful result should satisfy all of the following:

- The USB identity remains `2CA3:4006`.
- `usbnet=1`.
- `usbcfg` and `usbid` remain unchanged.
- An Ethernet device appears in iPhone / iPad settings and provides Internet access.

## Included tools

- `scripts/detect_device.ps1`: read-only target USB enumeration on Windows.
- `scripts/probe_at.py`: sends allowlisted queries only after validating the Windows VID/PID and PnP ancestry.
- `scripts/probe_at_linux.py`: sends allowlisted queries only after validating the Linux sysfs ancestry.
- `scripts/enable_ecm.py`: performs only the baseline-checked `usbnet=0 → 1` change and optional controlled reboot.
- `tests/test_safety.py`: verifies that unrelated devices and commands outside the workflow are rejected.

The toolkit does not provide arbitrary AT-command passthrough or bulk configuration.

## Further documentation

- [Windows / WSL2 setup](docs/en/windows-wsl-setup.md)
- [Technical notes and validation boundaries](docs/en/technical-notes.md)
- [Restoring `usbnet=0`](docs/en/recovery.md)

Never submit an IMEI, IMSI, ICCID, phone number, APN credential, eSIM profile, or other private SIM data. This project is not affiliated with DJI, Baiwang, or any carrier. It is released under the [MIT License](LICENSE).
