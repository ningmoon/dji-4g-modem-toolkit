[中文](../windows-wsl-setup.md) | [English](windows-wsl-setup.md)

# Windows / WSL2 setup

When Windows does not expose a usable AT serial port for `2CA3:4006`, WSL2, Ubuntu, and `usbipd-win` can provide temporary access to the module. USB attachment and Linux driver binding are temporary host state; they do not change the module configuration.

## Verified environment

- Windows 10 Pro build 19045
- WSL2 Ubuntu with kernel `6.18.33.2-microsoft-standard-WSL2`
- `usbipd-win`
- Python 3, `usbutils`, and the `usbserial` and `option` kernel modules in Ubuntu
- Target device: `2ca3:4006 Baiwang`

Other version combinations may behave differently. Install WSL2 using Microsoft's documentation and obtain `usbipd-win` from its official distribution channel.

## Attach the target device to WSL2

List USB devices in PowerShell:

```powershell
usbipd list
```

Select only the BUSID whose VID:PID is exactly `2CA3:4006`. A BUSID is not a stable identity and must be checked again before every operation.

The first share operation requires an elevated PowerShell session:

```powershell
usbipd bind --busid <BUSID>
```

Keep Ubuntu running, then attach the device:

```powershell
usbipd attach --wsl --busid <BUSID>
```

Confirm the device in Ubuntu:

```bash
lsusb
```

Continue only if `2ca3:4006` is present.

## Create a temporary AT port

The test module did not bind to the Linux serial driver automatically. The verified temporary binding sequence was:

```bash
sudo modprobe option
test -e /sys/bus/usb-serial/drivers/option1/new_id
printf '2ca3 4006\n' | sudo tee /sys/bus/usb-serial/drivers/option1/new_id
```

Several `/dev/ttyUSB*` nodes may appear. Do not infer the AT port from its number. First run:

```bash
sudo python3 scripts/probe_at_linux.py --list
```

On the test module, the AT function was USB interface `02`, mapped at that time to `/dev/ttyUSB2`. The actual node may differ.

Verify communication using a read-only `AT` query:

```bash
sudo python3 scripts/probe_at_linux.py --port /dev/ttyUSB2 --command AT
```

The script re-checks the VID/PID and USB interface through sysfs, reducing the risk of operating on another serial device attached to the host.

## Behavior after reboot

After `AT+CFUN=1,1`, the USB device disconnects and re-enumerates. The WSL attachment and temporary driver binding may be lost; this is expected. To regain access, start again with `usbipd list` and re-verify the BUSID, VID/PID, and port mapping.

After switching to `usbnet=1`, the Linux `option` driver may incorrectly claim the ECM interfaces. This affects ECM validation inside WSL only; it does not prevent direct use with an iPhone or iPad. Do not modify the VID/PID, `usbcfg`, or `usbid` to work around native Windows networking.

## Windows limitation

The tested Windows 10 host enumerated `2CA3:4006` but did not create a usable native ECM network adapter. Once the USB device is attached to WSL, its network interface belongs to WSL and does not automatically become a Windows network connection. This project did not use a modified INF, disable driver-signature enforcement, enable test signing, or change the USB identity.
