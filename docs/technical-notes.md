# 技术说明与验证边界

## 为什么只改 `usbnet`

验证样机原始 `usbnet=0`，网络协议不是 Apple 设备可直接使用的 CDC-ECM。将它改为 `usbnet=1` 后，模块暴露标准 ECM control/data interfaces，iPhone 和 iPad 可将其识别为 USB Ethernet 设备。

唯一的持久化改动是：

```text
AT+QCFG="usbnet",1
```

随后执行一次 `AT+CFUN=1,1` 让 USB composition 重新枚举。整个过程中没有修改 `usbcfg`、`usbid`、VID/PID、APN、SIM/eSIM 或固件。

## 已验证基线

| 项目 | 值 |
|---|---|
| 产品 | Baiwang QDC507 |
| Revision | `QDC507GLEFM21` |
| Firmware | `QDC507GLEFM21_01.001.02.004` |
| VID:PID | `2CA3:4006` |
| AT function | USB interface `02` |
| 原始 `usbnet` | `0` |
| 当前 `usbnet` | `1` |
| `usbcfg` | `0x2CA3,0x4006,1,1,1,1,1,0,0`（未改变） |
| `usbid` | `11427,16390`（未改变） |

## 验证结果

| 平台 | 状态 | 说明 |
|---|---|---|
| iPhone / iOS | PASS | 直接连接后识别 USB Ethernet 并成功联网；未记录具体 iOS 版本。 |
| iPad / iPadOS | PASS | 直接连接后识别 USB Ethernet 并成功联网；未记录具体 iPadOS 版本。 |
| Linux / WSL2 | PASS | ECM 获得 DHCP 地址，并验证模块网关和公网 IPv4 可达。 |
| Windows 10 Native | BLOCKED | 正常枚举 USB，但没有匹配的原生 ECM 网络适配器。 |
| macOS | NOT TESTED | 没有实测记录。 |

## 转换工具实机验证

`scripts/enable_ecm.py` 已在上述验证样机上完成实机测试：成功识别 `2CA3:4006` / interface `02`，读取并核对全部基线，在 `usbnet=1` 状态下保持幂等且不重复写入，并成功执行一次受控重启；重启后 VID:PID、`usbnet`、`usbcfg` 和 `usbid` 均保持预期值。

该样机此前已经通过人工受控流程完成 `usbnet=0 → 1`，因此本次脚本测试没有为了重演写入而先回退设备。脚本的真实设备识别、读取和重启路径已经验证；脚本中的 `AT+QCFG="usbnet",1` 写入分支由离线自动化测试覆盖，但尚未在另一块保持 `usbnet=0` 的实物上执行。

## 安全边界

- 另一块外观相同的模块也必须先读取自己的型号、固件和配置基线。
- `2CA3:4006` 只能作为必要条件，不能单独证明某个串口就是目标 AT 端口。
- 不要通过修改 VID/PID、`usbcfg`、`usbid` 或安装来源不明的驱动来绕过主机兼容性问题。
- Apple 测试只证明验证样机可用，不保证所有设备、系统、运营商、线材和供电条件。
- WSL 中的 USB binding、网络接口、DHCP 地址和 route 都是临时主机状态，不会随模块移动。

## 隐私

IMEI、IMSI、ICCID、电话号码、APN 凭据和 eSIM 信息不属于复现所需数据，不应记录到 issue、日志或提交中。
