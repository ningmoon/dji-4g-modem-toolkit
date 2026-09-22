[简体中文](README.md) | [English](README_EN.md)

# DJI 4G 模块 iPhone / iPad ECM 工具包

最近大疆一代 4G 模块比较火🔥，就搞了一块试试，可玩性比较强，但是也因此二手市场被炒的比较高，性价比不高。

![大疆一代 4G 模块](docs/assets/model-pic%20%285%29.jpg)

![大疆一代 4G 模块 SIM 卡槽](docs/assets/model-pic%20%284%29%20.jpg)

本项目不涉及VoHive方案，只是把大疆一代 4G 模块（Baiwang QDC507）的 USB 网络模式从 `usbnet=0` 切换为 `usbnet=1`（CDC-ECM），使其可作为 iPhone / iPad 的 USB 有线网络设备使用，是实现外挂模块上网的最小代价。

<img src="docs/assets/model-pic%20%281%29.jpg" alt="大疆 4G 模块连接 iPad" width="720">

本项目只改变一个持久化配置项：`usbnet`。它不刷写固件，不修改 VID/PID、`usbcfg`、`usbid`、APN 或 SIM/eSIM 配置。

## 已验证范围

验证样机：

- 产品：Baiwang QDC507（大疆一代 4G 模块）
- 固件：`QDC507GLEFM21_01.001.02.004`
- USB VID:PID：`2CA3:4006`
- 原始模式：`usbnet=0`
- 目标模式：`usbnet=1`（ECM）

验证结果：

| 平台              | 结果                    |
| --------------- | --------------------- |
| iPhone          | 已实测可联网                |
| iPad            | 已实测可联网                |
| Linux / WSL2    | 已验证 ECM、DHCP 和公网 IPv4 |
| Windows 10 原生网络 | 不可用；缺少匹配的原生 ECM 驱动    |
| macOS           | 未测试                   |

测试只覆盖一块模块和一组软硬件环境，不代表所有模块、系统版本、运营商、线材或供电组合都兼容。

## 运行环境

- Python 3.10 或更高版本。
- Linux / WSL2 路径只使用 Python 标准库，不需要安装额外 Python package。
- Windows COM 口路径需要安装 `pyserial`：

```powershell
python -m pip install pyserial
```

Windows 没有可用 AT 串口时，还需要 WSL2、Ubuntu 和 `usbipd-win`；完整准备步骤见 [Windows / WSL2 准备](docs/windows-wsl-setup.md)。所有命令均应在仓库根目录执行。

## 开始之前

`usbnet` 是模块的持久化配置。写入前请确认：

1. 设备准确枚举为 `2CA3:4006`，并确认它是目标大疆 4G 模块。
2. AT 端口来自该设备的 USB interface `02`，不要凭 `/dev/ttyUSB*` 或 `COM*` 编号猜测。
3. 先读取并保存 `ATI`、固件、`usbnet`、`usbcfg` 和 `usbid`。
4. 写入和重启期间保持稳定供电。

如果在 Windows 上没有可用的 AT 串口，可按 [Windows / WSL2 准备](docs/windows-wsl-setup.md) 将模块临时连接到 Ubuntu。

## 最短操作流程

### 1. 确认设备和 AT 端口

Linux / WSL2 下可使用仓库中的只读探测脚本：

```bash
sudo python3 scripts/probe_at_linux.py --list
sudo python3 scripts/probe_at_linux.py --port /dev/ttyUSB2 --command AT
sudo python3 scripts/probe_at_linux.py --port /dev/ttyUSB2 --command ATI
sudo python3 scripts/probe_at_linux.py --port /dev/ttyUSB2 --command AT+QGMR
sudo python3 scripts/probe_at_linux.py --port /dev/ttyUSB2 --command 'AT+QCFG="usbnet"'
sudo python3 scripts/probe_at_linux.py --port /dev/ttyUSB2 --command 'AT+QCFG="usbcfg"'
sudo python3 scripts/probe_at_linux.py --port /dev/ttyUSB2 --command 'AT+QCFG="usbid"'
```

`/dev/ttyUSB2` 只是验证样机上的结果，必须以脚本和 sysfs 的实际映射为准。Windows 下可先运行 `scripts/detect_device.ps1` 做只读枚举，再使用 `scripts/probe_at.py` 查询经过校验的 COM 端口。

确认样机基线应为：

```text
usbnet=0
usbcfg=0x2CA3,0x4006,1,1,1,1,1,0,0
usbid=11427,16390
```

如果型号、固件或任一基线值不同，请停止，不要照搬后续写入。

### 2. 运行专用转换工具

转换工具只允许执行经过固定校验的 `usbnet=0 → 1` 流程，不接受用户提供的任意 AT 命令。确认端口后运行：

```bash
sudo python3 scripts/enable_ecm.py --port /dev/ttyUSB2 --reboot
```

Windows 上若已经存在经过校验的目标 COM 口，并安装了 `pyserial`，可运行：

```powershell
python scripts/enable_ecm.py --port COM7 --reboot
```

工具会：

1. 重新验证 VID:PID 和 AT interface `02`；
2. 核对型号、固件、`usbnet`、`usbcfg` 和 `usbid`；
3. 要求输入 `ENABLE` 后，仅发送一次 `AT+QCFG="usbnet",1`；
4. 立即 read-back，确认 `usbnet=1` 且其他两个值未改变；
5. 要求输入 `REBOOT` 后，才发送一次 `AT+CFUN=1,1`。

如果写入后 USB 立即重新枚举，工具会停止且不会发送重启命令。此时重新 attach 设备、恢复已验证的 AT 端口，然后再次运行同一命令；工具会识别已经存在的 `usbnet=1`，完成基线复核后只执行已授权的重启。

自动化场景可附加 `--yes` 跳过两次文字确认，但不会跳过任何设备或配置校验。

### 3. 连接 iPhone / iPad

模块重新枚举后，将它通过支持数据传输的 USB 线连接到 iPhone 或 iPad。系统应把它识别为 USB Ethernet / 以太网设备，并通过模块获取网络配置。

<img src="docs/assets/model-pic%20%282%29.jpg" alt="iPad 将模块识别为 Baiwang 以太网设备" width="720">

成功时应满足：

- USB identity 仍为 `2CA3:4006`；
- `usbnet=1`；
- `usbcfg` 和 `usbid` 未改变；
- iPhone / iPad 设置中出现以太网设备并能访问网络。

## 仓库中的工具

- `scripts/detect_device.ps1`：Windows 下只读枚举目标 USB 设备。
- `scripts/probe_at.py`：Windows 下只允许向经过 VID/PID 和 PnP ancestry 校验的端口发送白名单查询。
- `scripts/probe_at_linux.py`：Linux / WSL2 下只允许向经过 sysfs 校验的端口发送白名单查询。
- `scripts/enable_ecm.py`：只执行经过基线校验的 `usbnet=0 → 1` 和可选受控重启。
- `tests/test_safety.py`：验证写命令和无关设备会被拒绝。

工具不提供任意 AT 命令透传或批量改写能力。

## 更多说明

- [Windows / WSL2 准备](docs/windows-wsl-setup.md)
- [技术说明与验证边界](docs/technical-notes.md)
- [恢复到 `usbnet=0`](docs/recovery.md)

请勿提交 IMEI、IMSI、ICCID、电话号码、APN 凭据、eSIM profile 或其他 SIM 私密数据。本项目与 DJI、Baiwang 或运营商无隶属关系，按 [MIT License](LICENSE) 发布。
