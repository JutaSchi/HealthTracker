"""Connect to the HealthTracker nRF54L15 DK over Bluetooth LE and print status."""

import asyncio
from datetime import datetime

from bleak import BleakClient, BleakScanner
from bleak.exc import BleakError

SERVICE_UUID = "7b5e0001-9b2a-4c7a-8f5e-4d2c6a110001"
STATUS_CHARACTERISTIC_UUID = "7b5e0002-9b2a-4c7a-8f5e-4d2c6a110001"
SCAN_TIMEOUT_SECONDS = 8.0


def on_status_notification(_sender: int, data: bytearray) -> None:
    """Print one status update received from the DK."""
    timestamp = datetime.now().strftime("%H:%M:%S")
    message = data.decode("utf-8", errors="replace")
    print(f"[{timestamp}] DK: {message}", flush=True)


def advertises_healthtracker_service(_device, advertisement) -> bool:
    """Match the DK by its custom service UUID, not by its changeable address."""
    advertised_uuids = {
        uuid.lower() for uuid in (advertisement.service_uuids or [])
    }
    return SERVICE_UUID in advertised_uuids


async def run() -> None:
    print("HealthTracker PC client started. Press Ctrl+C to quit.")

    while True:
        print("Scanning for the nRF54L15 DK...")
        try:
            device = await BleakScanner.find_device_by_filter(
                advertises_healthtracker_service,
                timeout=SCAN_TIMEOUT_SECONDS,
            )
            if device is None:
                print("DK not found; scanning again.")
                continue

            print(f"Found {device.name or 'HealthTracker DK'}; connecting...")
            async with BleakClient(device) as client:
                print("Connected. Waiting for status notifications...")
                await client.start_notify(
                    STATUS_CHARACTERISTIC_UUID,
                    on_status_notification,
                )
                while client.is_connected:
                    await asyncio.sleep(1)

        except BleakError as exc:
            print(f"Bluetooth error: {exc}")
            await asyncio.sleep(2)
        except OSError as exc:
            print(f"Bluetooth adapter error: {exc}")
            await asyncio.sleep(2)


if __name__ == "__main__":
    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        print("\nExiting.")
