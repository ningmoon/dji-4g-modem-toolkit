[中文](recovery.md) | [English](en/recovery.md)

# 恢复到 `usbnet=0`

验证样机的原始网络模式是 `usbnet=0`，当前模式是 `usbnet=1`。下面的回退思路基于原始配置，但尚未在该样机上实际执行，因此属于 **UNVERIFIED** 操作。

## 回退前检查

1. 确认设备为目标 `2CA3:4006` 模块，并证明 AT 端口来自 USB interface `02`。
2. 保存当前 `ATI`、固件、`usbnet`、`usbcfg` 和 `usbid` 输出。
3. 确认 `usbcfg=0x2CA3,0x4006,1,1,1,1,1,0,0`、`usbid=11427,16390`，且没有其他未记录改动。
4. 保证写入和重启期间供电稳定。

任何一项不一致都应停止。

## 预期回退命令

在已经确认的 AT 端口上发送：

```text
AT+QCFG="usbnet",0
AT+QCFG="usbnet"
AT+QCFG="usbcfg"
AT+QCFG="usbid"
```

只有 read-back 显示 `usbnet=0`，且 `usbcfg`、`usbid` 未改变时，才执行：

```text
AT+CFUN=1,1
```

USB 重新枚举后，再次验证 VID:PID、USB interfaces 和全部三个配置值。回退到 `usbnet=0` 后，iPhone / iPad 的 ECM 即插即用能力预计会消失。
