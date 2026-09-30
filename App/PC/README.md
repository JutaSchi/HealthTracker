# HealthTracker PC BLE client

This Python app scans for and connects to the **HealthTracker-54L15** BLE service, then prints status notifications from the nRF54L15 DK. The current firmware sends a device uptime message every two seconds; sensor readings are not wired into the BLE payload yet.

## Run

1. Flash the firmware from `firmware/` to the nRF54L15 DK and power it on.
2. On the PC, open a terminal in `App/PC/` and install the dependency:

   ```sh
   python -m pip install -r requirements.txt
   ```

3. Start the client:

   ```sh
   python app.py
   ```

The app reconnects automatically if the DK is not found or disconnects. Your PC needs a working Bluetooth LE adapter and OS Bluetooth support enabled.

## BLE roles

The DK advertises as a connectable BLE peripheral. The PC app scans and connects as the BLE central, then subscribes to the status characteristic. Although this is often described as “the DK connecting to the PC,” the PC initiates the BLE connection in this setup.

The service and characteristic UUIDs are defined in `firmware/src/main.c` and mirrored in `app.py`; keep them in sync if you change them.
