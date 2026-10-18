"""Describe the PC's hardware. Read-only: CIM queries and registry reads only."""
from __future__ import annotations

import platform
import sys

from landfall.scan.winutil import run_powershell_json

HW_SCRIPT = r"""
$ErrorActionPreference = 'SilentlyContinue'
$cs  = Get-CimInstance Win32_ComputerSystem
$out = [ordered]@{
  cpu      = @(Get-CimInstance Win32_Processor | ForEach-Object { $_.Name.Trim() })
  ram_gb   = [math]::Round($cs.TotalPhysicalMemory / 1GB, 1)
  model    = ("$($cs.Manufacturer) $($cs.Model)").Trim()
  gpu      = @(Get-CimInstance Win32_VideoController | ForEach-Object { $_.Name })
  wifi     = @(Get-NetAdapter -Physical | Where-Object { $_.PhysicalMediaType -match '802\.11' } | ForEach-Object { $_.InterfaceDescription })
  ethernet = @(Get-NetAdapter -Physical | Where-Object { $_.PhysicalMediaType -match '802\.3' } | ForEach-Object { $_.InterfaceDescription })
  bluetooth= @(Get-PnpDevice -Class Bluetooth -PresentOnly | Where-Object { $_.FriendlyName -notmatch 'Enumerator|RFCOMM|LE Generic|Service' } | ForEach-Object { $_.FriendlyName })
  webcam   = @(Get-PnpDevice -Class Camera,Image -PresentOnly | ForEach-Object { $_.FriendlyName })
  printers = @(Get-CimInstance Win32_Printer | Where-Object { $_.Name -notmatch 'PDF|XPS|OneNote|Fax' } | ForEach-Object { $_.Name })
  disks    = @(Get-CimInstance Win32_DiskDrive | ForEach-Object { "$($_.Model) ($([math]::Round($_.Size / 1GB)) GB)" })
}
$out | ConvertTo-Json -Compress -Depth 3
"""


def firmware_type() -> str:
    """'UEFI', 'Legacy BIOS' or 'Unknown' via kernel32.GetFirmwareType (no admin needed)."""
    if sys.platform != "win32":
        return "Unknown"
    try:
        import ctypes
        value = ctypes.c_uint(0)
        if ctypes.windll.kernel32.GetFirmwareType(ctypes.byref(value)):
            return {1: "Legacy BIOS", 2: "UEFI"}.get(value.value, "Unknown")
    except (OSError, AttributeError):
        pass
    return "Unknown"


def secure_boot() -> str:
    if sys.platform != "win32":
        return "Unknown"
    if firmware_type() == "Legacy BIOS":
        return "Not used (Legacy BIOS)"
    try:
        import winreg
        path = r"SYSTEM\CurrentControlSet\Control\SecureBoot\State"
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, path, 0, winreg.KEY_READ) as key:
            return "On" if winreg.QueryValueEx(key, "UEFISecureBootEnabled")[0] == 1 else "Off"
    except OSError:
        return "Unknown"


def _as_list(value) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(v).strip() for v in value if v]
    return [str(value).strip()] if value else []


def scan_hardware() -> dict:
    raw = (run_powershell_json(HW_SCRIPT, timeout=90) or [{}])[0]
    return {
        "windows": f"{platform.system()} {platform.release()} ({platform.version()})",
        "model": str(raw.get("model", "")) or "Unknown",
        "cpu": _as_list(raw.get("cpu")),
        "ram_gb": raw.get("ram_gb") or 0,
        "gpu": _as_list(raw.get("gpu")),
        "wifi": _as_list(raw.get("wifi")),
        "ethernet": _as_list(raw.get("ethernet")),
        "bluetooth": _as_list(raw.get("bluetooth")),
        "webcam": _as_list(raw.get("webcam")),
        "printers": _as_list(raw.get("printers")),
        "disks": _as_list(raw.get("disks")),
        "boot_mode": firmware_type(),
        "secure_boot": secure_boot(),
    }


def hardware_notes(hw: dict) -> list[str]:
    """Plain-English heads-ups about hardware that can need extra care on Linux."""
    notes = []
    gpus = " ".join(hw.get("gpu", [])).lower()
    if "nvidia" in gpus:
        notes.append("NVIDIA graphics: pick a Linux version that offers NVIDIA drivers during "
                     "install (Ubuntu, Linux Mint and Pop!_OS all do).")
    wifi = " ".join(hw.get("wifi", [])).lower()
    if "broadcom" in wifi:
        notes.append("Broadcom Wi-Fi: may need an extra driver. Keep an Ethernet cable or "
                     "phone tethering handy for the first boot.")
    if hw.get("ram_gb") and hw["ram_gb"] < 4:
        notes.append("Under 4 GB of RAM: choose a lighter desktop such as Linux Mint Xfce or Lubuntu.")
    if hw.get("secure_boot") == "On":
        notes.append("Secure Boot is on. Ubuntu, Mint and Fedora work with it on; some other "
                     "versions need it turned off.")
    if hw.get("boot_mode") == "Legacy BIOS":
        notes.append("This PC starts in Legacy BIOS mode. Linux works fine; just install Linux "
                     "in the same mode.")
    return notes
