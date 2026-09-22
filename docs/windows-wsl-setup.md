[中文](windows-wsl-setup.md) | [English](en/windows-wsl-setup.md)

# Windows / WSL2 准备

当 Windows 没有为 `2CA3:4006` 提供可用 AT 串口时，可以借助 WSL2、Ubuntu 和 `usbipd-win` 临时访问模块。这里的 USB attachment 和 Linux driver binding 都是主机临时状态，不会修改模块配置。

## 已验证环境

- Windows 10 Pro build 19045
- WSL2 Ubuntu，kernel `6.18.33.2-microsoft-standard-WSL2`
- `usbipd-win`
- Ubuntu 中的 Python 3、`usbutils` 和内核模块 `usbserial`、`option`
- 目标设备：`2ca3:4006 Baiwang`

其他版本可能有不同表现。请使用 Microsoft 文档安装 WSL2，并从官方发行渠道安装 `usbipd-win`。

## 将目标设备连接到 WSL2

在 PowerShell 中列出 USB 设备：

```powershell
usbipd list
```

只选择 VID:PID 准确为 `2CA3:4006` 的 BUSID。BUSID 会变化，每次操作前都应重新确认。

首次共享设备需要管理员 PowerShell：

```powershell
usbipd bind --busid <BUSID>
```

保持 Ubuntu 正在运行，然后连接设备：

```powershell
usbipd attach --wsl --busid <BUSID>
```

在 Ubuntu 中确认：

```bash
lsusb
```

只有看到 `2ca3:4006` 后才继续。

## 创建临时 AT 端口

验证样机不会自动绑定 Linux serial driver。使用过的临时绑定方式为：

```bash
sudo modprobe option
test -e /sys/bus/usb-serial/drivers/option1/new_id
printf '2ca3 4006\n' | sudo tee /sys/bus/usb-serial/drivers/option1/new_id
```

之后可能出现多个 `/dev/ttyUSB*`。不要从编号推断 AT 端口；先运行：

```bash
sudo python3 scripts/probe_at_linux.py --list
```

验证样机的 AT function 是 USB interface `02`，当时对应 `/dev/ttyUSB2`。实际节点可能不同。

通过只读 `AT` 确认通信：

```bash
sudo python3 scripts/probe_at_linux.py --port /dev/ttyUSB2 --command AT
```

脚本会重新检查 sysfs 中的 VID/PID 和 USB interface，避免误操作同一主机上的其他串口设备。

## 重启后的行为

执行 `AT+CFUN=1,1` 后，USB 会断开并重新枚举，WSL attachment 和临时 driver binding 可能丢失。这是正常现象。需要继续读取模块时，从 `usbipd list` 开始重新确认 BUSID、VID/PID 和端口映射。

切换到 `usbnet=1` 后，Linux 的 `option` driver 可能错误占用 ECM interfaces；这只影响在 WSL 内验证 ECM，不影响模块直接连接 iPhone / iPad。不要为了修复 Windows 原生联网而修改 VID/PID、`usbcfg` 或 `usbid`。

## Windows 限制

验证用 Windows 10 能枚举 `2CA3:4006`，但没有创建可用的原生 ECM 网络适配器。把 USB 设备 attach 到 WSL 后，网络接口属于 WSL，也不会自动成为 Windows 的网络连接。本项目未使用修改 INF、关闭驱动签名、test signing 或更改 USB identity 的方案。
