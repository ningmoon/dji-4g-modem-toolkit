[中文](../recovery.md) | [English](recovery.md)

# Restoring `usbnet=0`

The test module originally used `usbnet=0` and currently uses `usbnet=1`. The rollback outline below is based on the recorded original configuration, but it has not been executed on this module and must be treated as **UNVERIFIED**.

## Checks before rollback

1. Confirm that the device is the target `2CA3:4006` module and prove that the AT port belongs to USB interface `02`.
2. Save the current `ATI`, firmware, `usbnet`, `usbcfg`, and `usbid` responses.
3. Confirm `usbcfg=0x2CA3,0x4006,1,1,1,1,1,0,0` and `usbid=11427,16390`, with no other unrecorded changes.
4. Ensure stable power throughout the write and reboot.

Stop if any check differs.

## Expected rollback commands

On the verified AT port, send:

```text
AT+QCFG="usbnet",0
AT+QCFG="usbnet"
AT+QCFG="usbcfg"
AT+QCFG="usbid"
```

Only if read-back reports `usbnet=0` while `usbcfg` and `usbid` remain unchanged, send:

```text
AT+CFUN=1,1
```

After USB re-enumeration, verify the VID:PID, USB interfaces, and all three configuration values again. Returning to `usbnet=0` is expected to remove the plug-and-play ECM behavior on iPhone and iPad.
