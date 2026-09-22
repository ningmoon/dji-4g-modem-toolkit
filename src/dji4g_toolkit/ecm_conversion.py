"""Fail-closed orchestration for the single supported usbnet=0 -> 1 change."""

from dataclasses import dataclass
import re
from typing import Callable


EXPECTED_MODEL = "QDC507"
EXPECTED_FIRMWARE = "QDC507GLEFM21_01.001.02.004"
EXPECTED_USBCFG = "0x2CA3,0x4006,1,1,1,1,1,0,0"
EXPECTED_USBID = "11427,16390"

SET_ECM_COMMAND = 'AT+QCFG="usbnet",1'
REBOOT_COMMAND = "AT+CFUN=1,1"


class ConversionError(RuntimeError):
    """The conversion stopped before it could safely continue."""


class PostWriteVerificationError(ConversionError):
    """The write returned OK, but the required read-back could not complete."""


@dataclass(frozen=True)
class Baseline:
    model_response: str
    firmware: str
    usbnet: int
    usbcfg: str
    usbid: str


@dataclass(frozen=True)
class ConversionResult:
    before: Baseline
    after: Baseline
    changed: bool
    rebooted: bool


Exchange = Callable[[str], str]
Authorize = Callable[[str], bool]


def _require_ok(command: str, response: str) -> None:
    if not re.search(r"(?:^|[\r\n])OK(?:[\r\n]|$)", response, re.IGNORECASE):
        raise ConversionError(f"{command} did not return OK")


def _qcfg_value(name: str, response: str) -> str:
    # QDC507 reports usbid without the quoted key, while usbnet/usbcfg include it.
    if name == "usbid":
        pattern = r'\+QCFG:\s*(?:"usbid"\s*,\s*)?([^\r\n]+)'
    else:
        pattern = rf'\+QCFG:\s*"{re.escape(name)}"\s*,\s*([^\r\n]+)'
    match = re.search(pattern, response, re.IGNORECASE)
    if not match:
        raise ConversionError(f"Cannot parse {name} response")
    return re.sub(r"\s+", "", match.group(1))


def read_baseline(exchange: Exchange) -> Baseline:
    responses: dict[str, str] = {}
    for command in (
        "AT",
        "ATI",
        "AT+QGMR",
        'AT+QCFG="usbnet"',
        'AT+QCFG="usbcfg"',
        'AT+QCFG="usbid"',
    ):
        response = exchange(command)
        _require_ok(command, response)
        responses[command] = response

    model_response = responses["ATI"]
    if EXPECTED_MODEL not in model_response:
        raise ConversionError(f"Unexpected model; required marker {EXPECTED_MODEL!r} was not returned")

    firmware_response = responses["AT+QGMR"]
    if EXPECTED_FIRMWARE not in firmware_response:
        raise ConversionError(
            f"Unexpected firmware; expected {EXPECTED_FIRMWARE!r}"
        )

    usbnet_text = _qcfg_value("usbnet", responses['AT+QCFG="usbnet"'])
    if usbnet_text not in {"0", "1"}:
        raise ConversionError(f"Unexpected usbnet value: {usbnet_text!r}")

    baseline = Baseline(
        model_response=model_response,
        firmware=EXPECTED_FIRMWARE,
        usbnet=int(usbnet_text),
        usbcfg=_qcfg_value("usbcfg", responses['AT+QCFG="usbcfg"']),
        usbid=_qcfg_value("usbid", responses['AT+QCFG="usbid"']),
    )
    if baseline.usbcfg.casefold() != EXPECTED_USBCFG.casefold():
        raise ConversionError(f"Unexpected usbcfg: {baseline.usbcfg!r}")
    if baseline.usbid != EXPECTED_USBID:
        raise ConversionError(f"Unexpected usbid: {baseline.usbid!r}")
    return baseline


def enable_ecm(
    exchange: Exchange,
    authorize: Authorize,
    *,
    reboot: bool = False,
) -> ConversionResult:
    """Validate the exact baseline, make at most one setting write, then verify."""

    before = read_baseline(exchange)
    changed = False
    after = before

    if before.usbnet == 0:
        if not authorize("ENABLE"):
            raise ConversionError("ECM enable was not authorized")
        response = exchange(SET_ECM_COMMAND)
        _require_ok(SET_ECM_COMMAND, response)
        changed = True
        try:
            after = read_baseline(exchange)
        except Exception as exc:
            raise PostWriteVerificationError(
                "usbnet write returned OK, but read-back failed. The USB device may have "
                "re-enumerated. Reattach it, restore the verified AT port, and rerun this "
                "tool before requesting a reboot."
            ) from exc
        if after.usbnet != 1:
            raise PostWriteVerificationError("Read-back did not confirm usbnet=1")
        if (after.usbcfg.casefold(), after.usbid) != (
            before.usbcfg.casefold(), before.usbid,
        ):
            raise PostWriteVerificationError("usbcfg or usbid changed unexpectedly")

    rebooted = False
    if reboot:
        if after.usbnet != 1:
            raise ConversionError("Refused reboot: usbnet=1 has not been verified")
        if not authorize("REBOOT"):
            raise ConversionError("Controlled reboot was not authorized")
        response = exchange(REBOOT_COMMAND)
        _require_ok(REBOOT_COMMAND, response)
        rebooted = True

    return ConversionResult(before=before, after=after, changed=changed, rebooted=rebooted)
