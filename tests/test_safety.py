"""Offline safety checks: no COM port is opened or AT command sent."""

import sys
import types
import unittest
import json
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from dji4g_toolkit.at_query import validate_command, validate_ecm_workflow_command
from dji4g_toolkit.ecm_conversion import (
    ConversionError,
    PostWriteVerificationError,
    REBOOT_COMMAND,
    SET_ECM_COMMAND,
    enable_ecm,
)
from dji4g_toolkit.serial_probe import verify_usb_port


class FakeModem:
    def __init__(self, *, usbnet=0, usbcfg="0x2CA3,0x4006,1,1,1,1,1,0,0",
                 usbid="11427,16390", disconnect_after_write=False):
        self.usbnet = usbnet
        self.usbcfg = usbcfg
        self.usbid = usbid
        self.disconnect_after_write = disconnect_after_write
        self.commands = []
        self.write_completed = False

    def __call__(self, command):
        self.commands.append(command)
        if self.disconnect_after_write and self.write_completed:
            raise OSError("device detached")
        responses = {
            "AT": "AT\r\r\nOK\r\n",
            "ATI": "ATI\r\r\nBaiwang\r\nQDC507\r\nOK\r\n",
            "AT+QGMR": "AT+QGMR\r\r\nQDC507GLEFM21_01.001.02.004\r\nOK\r\n",
            'AT+QCFG="usbnet"': f'\r\n+QCFG: "usbnet",{self.usbnet}\r\nOK\r\n',
            'AT+QCFG="usbcfg"': f'\r\n+QCFG: "usbcfg",{self.usbcfg}\r\nOK\r\n',
            'AT+QCFG="usbid"': f"\r\n+QCFG: {self.usbid}\r\nOK\r\n",
            REBOOT_COMMAND: "\r\nOK\r\n",
        }
        if command == SET_ECM_COMMAND:
            self.usbnet = 1
            self.write_completed = True
            return "\r\nOK\r\n"
        return responses[command]


class SafetyTests(unittest.TestCase):
    def test_exact_query_allowlist(self):
        self.assertEqual(validate_command('AT+QCFG="usbnet"'), 'AT+QCFG="usbnet"')
        self.assertEqual(validate_command('AT+QGMR'), 'AT+QGMR')
        self.assertEqual(validate_command('AT+CEREG?'), 'AT+CEREG?')
        for command in ('AT+QCFG="usbnet",1', 'AT+QCFG="usbcfg",1',
                        'AT+QCFG="usbid",1', 'AT+CFUN=1,1'):
            with self.subTest(command=command), self.assertRaises(ValueError):
                validate_command(command)

    def test_ecm_workflow_allowlist_is_narrow(self):
        self.assertEqual(validate_ecm_workflow_command(SET_ECM_COMMAND), SET_ECM_COMMAND)
        self.assertEqual(validate_ecm_workflow_command(REBOOT_COMMAND), REBOOT_COMMAND)
        for command in ('AT+QCFG="usbnet",0', 'AT+QCFG="usbcfg",1',
                        'AT+QCFG="usbid",1', 'AT+CFUN=1'):
            with self.subTest(command=command), self.assertRaises(ValueError):
                validate_ecm_workflow_command(command)

    def test_ecm_conversion_exact_sequence(self):
        modem = FakeModem()
        result = enable_ecm(modem, lambda action: action in {"ENABLE", "REBOOT"}, reboot=True)
        self.assertTrue(result.changed)
        self.assertTrue(result.rebooted)
        self.assertEqual(result.after.usbnet, 1)
        self.assertEqual(modem.commands.count(SET_ECM_COMMAND), 1)
        self.assertEqual(modem.commands.count(REBOOT_COMMAND), 1)

    def test_ecm_conversion_requires_authorization(self):
        modem = FakeModem()
        with self.assertRaises(ConversionError):
            enable_ecm(modem, lambda _action: False, reboot=True)
        self.assertNotIn(SET_ECM_COMMAND, modem.commands)
        self.assertNotIn(REBOOT_COMMAND, modem.commands)

    def test_ecm_conversion_refuses_unexpected_baseline(self):
        modem = FakeModem(usbcfg="0x2CA3,0x4006,0,0,0,0,0,0,0")
        with self.assertRaises(ConversionError):
            enable_ecm(modem, lambda _action: True, reboot=True)
        self.assertNotIn(SET_ECM_COMMAND, modem.commands)
        self.assertNotIn(REBOOT_COMMAND, modem.commands)

    def test_ecm_conversion_never_reboots_without_readback(self):
        modem = FakeModem(disconnect_after_write=True)
        with self.assertRaises(PostWriteVerificationError):
            enable_ecm(modem, lambda _action: True, reboot=True)
        self.assertEqual(modem.commands.count(SET_ECM_COMMAND), 1)
        self.assertNotIn(REBOOT_COMMAND, modem.commands)

    def test_already_enabled_is_idempotent(self):
        modem = FakeModem(usbnet=1)
        result = enable_ecm(modem, lambda action: action == "REBOOT", reboot=True)
        self.assertFalse(result.changed)
        self.assertTrue(result.rebooted)
        self.assertNotIn(SET_ECM_COMMAND, modem.commands)
        self.assertEqual(modem.commands.count(REBOOT_COMMAND), 1)

    def test_other_usb_device_refused_before_pnp_lookup(self):
        item = types.SimpleNamespace(device="COM7", vid=0x2C7C, pid=0x0127)
        list_ports = types.SimpleNamespace(comports=lambda: [item])
        with patch.dict(sys.modules, {
            "serial": types.ModuleType("serial"),
            "serial.tools": types.ModuleType("serial.tools"),
            "serial.tools.list_ports": list_ports,
        }), patch("dji4g_toolkit.serial_probe.sys.platform", "win32"), \
                patch("dji4g_toolkit.serial_probe.subprocess.run") as run:
            with self.assertRaises(ValueError):
                verify_usb_port("COM7", 0x2CA3, 0x4006)
            run.assert_not_called()

    def test_invalid_port_refused(self):
        with self.assertRaises(ValueError):
            verify_usb_port("COM8;something", 0x2CA3, 0x4006)

    def test_pnp_chain_requires_mi02_hardware_id(self):
        item = types.SimpleNamespace(device="COM7", vid=0x2CA3, pid=0x4006)
        list_ports = types.SimpleNamespace(comports=lambda: [item])
        instance = r"USB\VID_2CA3&PID_4006&MI_02\6&53FA1FD&0&0002"
        record = {"InstanceId": instance, "HardwareIds": [r"USB\VID_2CA3&PID_4006&MI_02"]}
        with patch.dict(sys.modules, {
            "serial": types.ModuleType("serial"),
            "serial.tools": types.ModuleType("serial.tools"),
            "serial.tools.list_ports": list_ports,
        }), patch("dji4g_toolkit.serial_probe.sys.platform", "win32"), \
                patch("dji4g_toolkit.serial_probe.subprocess.run") as run:
            run.return_value = types.SimpleNamespace(stdout=json.dumps(record))
            verify_usb_port("COM7", 0x2CA3, 0x4006)
            record["HardwareIds"] = [r"USB\VID_2CA3&PID_4006&MI_03"]
            run.return_value = types.SimpleNamespace(stdout=json.dumps(record))
            with self.assertRaises(ValueError):
                verify_usb_port("COM7", 0x2CA3, 0x4006)


if __name__ == "__main__":
    unittest.main()
