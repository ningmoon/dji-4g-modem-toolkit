"""Exact allowlist for AT commands; unknown commands never reach serial.write."""

READ_ONLY_AT_COMMANDS = frozenset({
    "AT", "ATI", "AT+GMI", "AT+GMM", "AT+GMR",
    "AT+CGMI", "AT+CGMM", "AT+CGMR", "AT+QGMR", "AT+CPIN?",
    "AT+CSQ", "AT+CEREG?", "AT+COPS?", "AT+CGSN",
    'AT+QCFG="usbnet"', 'AT+QCFG="usbcfg"', 'AT+QCFG="usbid"',
})

# This is deliberately not a general write allowlist. These are the only two
# mutating commands used by the reviewed ECM conversion workflow.
ECM_WORKFLOW_COMMANDS = READ_ONLY_AT_COMMANDS | frozenset({
    'AT+QCFG="usbnet",1',
    "AT+CFUN=1,1",
})


def validate_command(command: str) -> str:
    if command not in READ_ONLY_AT_COMMANDS:
        raise ValueError("Refused: AT command is not in the exact read-only allowlist")
    return command


def validate_ecm_workflow_command(command: str) -> str:
    if command not in ECM_WORKFLOW_COMMANDS:
        raise ValueError("Refused: command is outside the fixed ECM conversion workflow")
    return command
