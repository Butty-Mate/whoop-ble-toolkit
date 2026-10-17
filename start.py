#!/usr/bin/env python3
"""Élő pulzus egy WHOOP pántról (vagy bármilyen BLE pulzusmérőről) macOS-en.

(180D / 2A37),

"""

import asyncio
import time

from bleak import BleakClient, BleakScanner

HR_SERVICE = "0000180d-0000-1000-8000-00805f9b34fb"
HR_MEASUREMENT = "00002a37-0000-1000-8000-00805f9b34fb"


def parse_hr(data: bytearray) -> tuple[int, list[float]]:
    """Heart Rate Measurement csomag -> (pulzus bpm, R-R intervallumok ms-ban)."""
    flags = data[0]
    i = 1
    if flags & 0x01:  # 16 bites pulzusérték
        bpm = int.from_bytes(data[i:i + 2], "little")
        i += 2
    else:             # 8 bites pulzusérték
        bpm = data[i]
        i += 1
    if flags & 0x08:  
        i += 2
    rr = []
    if flags & 0x10:  # R-R intervallumok, 1/1024 
        while i + 1 < len(data):
            raw = int.from_bytes(data[i:i + 2], "little")
            rr.append(raw / 1024 * 1000)
            i += 2
    return bpm, rr


def on_hr(_sender, data: bytearray) -> None:
    bpm, rr = parse_hr(data)
    rr_text = ", ".join(f"{x:.0f}" for x in rr) if rr else "-"
    print(f"{time.strftime('%H:%M:%S')}  {bpm:3d} bpm   R-R: {rr_text} ms")


async def find_device():
    print("Pánt keresése (10 mp)...")
    devices = await BleakScanner.discover(timeout=10.0, service_uuids=[HR_SERVICE])
    if not devices:
        
        devices = [d for d in await BleakScanner.discover(timeout=10.0)
                   if d.name and "whoop" in d.name.lower()]
    for d in devices:
        print(f"  talált: {d.name or '(névtelen)'}  {d.address}")
    whoop = [d for d in devices if d.name and "whoop" in d.name.lower()]
    return (whoop or devices or [None])[0]


async def main():
    device = await find_device()
    if device is None:
        print("Nem találtam pulzusmérőt")
        return
    print(f"Csatlakozás: {device.name}...")
    async with BleakClient(device) as client:
        await client.start_notify(HR_MEASUREMENT, on_hr)
        print("Csatlakozva. Kilépés: Ctrl+C\n")
        while client.is_connected:
            await asyncio.sleep(1)
    print("A kapcsolat megszakadt.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nKilépés.")