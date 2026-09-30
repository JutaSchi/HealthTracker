import sys
import asyncio
import re
from datetime import datetime

from bleak import BleakClient, BleakScanner
from bleak.exc import BleakError

from PySide6.QtCore import QObject, Signal, Slot, QThread
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QPlainTextEdit,
    QVBoxLayout,
    QWidget,
)


SERVICE_UUID = "7b5e0001-9b2a-4c7a-8f5e-4d2c6a110001"
STATUS_CHARACTERISTIC_UUID = "7b5e0002-9b2a-4c7a-8f5e-4d2c6a110001"

SCAN_TIMEOUT_SECONDS = 8.0
SENSOR_VALUES_PATTERN = re.compile(
    r"red=(-?\d+(?:\.\d+)?),\s*ir=(-?\d+(?:\.\d+)?)",
    re.IGNORECASE,
)


class BluetoothWorker(QObject):
    """
    Runs all Bleak/asyncio work outside the Qt GUI thread.
    """

    sensor_values = Signal(str, str)
    log_message = Signal(str)
    connected = Signal(str)
    disconnected = Signal()
    error = Signal(str)
    finished = Signal()

    def __init__(self):
        super().__init__()

        self.loop = None
        self.client = None
        self.running = False

    @Slot()
    def run(self):
        """
        Entry point executed inside the worker thread.
        """
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

        self.running = True

        try:
            self.loop.run_until_complete(self.bluetooth_loop())
        except Exception as exc:
            self.error.emit(f"Bluetooth worker error: {exc}")
        finally:
            self.running = False

            try:
                self.loop.close()
            except Exception:
                pass

            self.finished.emit()

    async def bluetooth_loop(self):
        """
        Continuously scan, connect, and listen for notifications.
        """

        while self.running:
            self.log_message.emit("Scanning for the nRF54L15 DK...")

            try:
                device = await BleakScanner.find_device_by_filter(
                    self.advertises_healthtracker_service,
                    timeout=SCAN_TIMEOUT_SECONDS,
                )

                if not self.running:
                    break

                if device is None:
                    self.log_message.emit(
                        "DK not found; scanning again."
                    )
                    continue

                name = device.name or "HealthTracker DK"

                self.log_message.emit(
                    f"Found {name}; connecting..."
                )

                async with BleakClient(device) as client:
                    self.client = client

                    if not client.is_connected:
                        self.error.emit(
                            "Failed to establish Bluetooth connection."
                        )
                        continue

                    self.connected.emit(name)

                    self.log_message.emit(
                        "Connected. Waiting for status notifications..."
                    )

                    await client.start_notify(
                        STATUS_CHARACTERISTIC_UUID,
                        self.on_status_notification,
                    )

                    try:
                        while (
                            self.running
                            and client.is_connected
                        ):
                            await asyncio.sleep(1)

                    finally:
                        try:
                            await client.stop_notify(
                                STATUS_CHARACTERISTIC_UUID
                            )
                        except Exception:
                            pass

                    self.client = None

                    if self.running:
                        self.log_message.emit(
                            "Device disconnected."
                        )
                        self.disconnected.emit()

            except BleakError as exc:
                self.error.emit(f"Bluetooth error: {exc}")

                if self.running:
                    await asyncio.sleep(2)

            except OSError as exc:
                self.error.emit(
                    f"Bluetooth adapter error: {exc}"
                )

                if self.running:
                    await asyncio.sleep(2)

            except Exception as exc:
                self.error.emit(
                    f"Unexpected Bluetooth error: {exc}"
                )

                if self.running:
                    await asyncio.sleep(2)

    @staticmethod
    def advertises_healthtracker_service(
        _device,
        advertisement,
    ) -> bool:
        """
        Match the DK using its advertised service UUID.

        This is preferable to matching its Bluetooth address because
        BLE addresses can change depending on the platform/device.
        """

        advertised_uuids = {
            uuid.lower()
            for uuid in (advertisement.service_uuids or [])
        }

        return SERVICE_UUID.lower() in advertised_uuids

    def on_status_notification(
        self,
        _sender: int,
        data: bytearray,
    ):
        """
        Called by Bleak whenever the DK sends a notification.
        """

        message = data.decode(
            "utf-8",
            errors="replace",
        )

        match = SENSOR_VALUES_PATTERN.search(message)
        if match is None:
            self.log_message.emit(f"DK status: {message}")
            return

        self.sensor_values.emit(*match.groups())

    @Slot()
    def stop(self):
        """
        Stop the Bluetooth worker.
        """

        self.running = False

        if self.loop and self.loop.is_running():
            asyncio.run_coroutine_threadsafe(
                self.disconnect(),
                self.loop,
            )

    async def disconnect(self):
        """
        Disconnect the active Bleak client.
        """

        if self.client is not None:
            try:
                await self.client.disconnect()
            except Exception:
                pass


class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()

        self.setWindowTitle("HealthTracker Bluetooth Client")
        self.resize(800, 500)

        self.thread = None
        self.worker = None

        self.setup_ui()

    def setup_ui(self):

        central = QWidget()
        self.setCentralWidget(central)

        layout = QVBoxLayout(central)

        # ---------------------------------------------------------
        # Header
        # ---------------------------------------------------------

        header_layout = QHBoxLayout()

        title = QLabel("HealthTracker DK")
        title.setStyleSheet(
            """
            QLabel {
                font-size: 22px;
                font-weight: bold;
            }
            """
        )

        self.status_label = QLabel("● Disconnected")

        self.status_label.setStyleSheet(
            """
            QLabel {
                color: #888;
                font-weight: bold;
            }
            """
        )

        header_layout.addWidget(title)
        header_layout.addStretch()
        header_layout.addWidget(self.status_label)

        layout.addLayout(header_layout)

        # ---------------------------------------------------------
        # Buttons
        # ---------------------------------------------------------

        button_layout = QHBoxLayout()

        self.start_button = QPushButton("Start Bluetooth")
        self.stop_button = QPushButton("Stop")
        self.clear_button = QPushButton("Clear Log")

        self.stop_button.setEnabled(False)

        button_layout.addWidget(self.start_button)
        button_layout.addWidget(self.stop_button)
        button_layout.addWidget(self.clear_button)
        button_layout.addStretch()

        layout.addLayout(button_layout)

        # ---------------------------------------------------------
        # Live sensor values
        # ---------------------------------------------------------

        readings_layout = QHBoxLayout()

        red_layout = QVBoxLayout()
        red_layout.addWidget(QLabel("RED · raw count"))
        self.red_value_label = QLabel("--")
        self.red_value_label.setStyleSheet(
            "font-size: 28px; font-weight: bold; color: #b23b3b;"
        )
        red_layout.addWidget(self.red_value_label)
        readings_layout.addLayout(red_layout)

        ir_layout = QVBoxLayout()
        ir_layout.addWidget(QLabel("IR · raw count"))
        self.ir_value_label = QLabel("--")
        self.ir_value_label.setStyleSheet(
            "font-size: 28px; font-weight: bold; color: #147d92;"
        )
        ir_layout.addWidget(self.ir_value_label)
        readings_layout.addLayout(ir_layout)

        layout.addLayout(readings_layout)

        self.last_sample_label = QLabel("Waiting for sensor samples")
        layout.addWidget(self.last_sample_label)

        # ---------------------------------------------------------
        # Log output
        # ---------------------------------------------------------

        self.log = QPlainTextEdit()

        self.log.setReadOnly(True)

        self.log.setStyleSheet(
            """
            QPlainTextEdit {
                font-family: Consolas, "Courier New", monospace;
                font-size: 13px;
            }
            """
        )

        layout.addWidget(self.log)

        # ---------------------------------------------------------
        # Signals
        # ---------------------------------------------------------

        self.start_button.clicked.connect(
            self.start_bluetooth
        )

        self.stop_button.clicked.connect(
            self.stop_bluetooth
        )

        self.clear_button.clicked.connect(
            self.log.clear
        )

    # -------------------------------------------------------------
    # Bluetooth
    # -------------------------------------------------------------

    def start_bluetooth(self):

        if self.thread is not None:
            return

        self.write_log(
            "HealthTracker PC client started."
        )

        self.write_log(
            "Searching for the HealthTracker DK..."
        )

        self.status_label.setText(
            "● Scanning..."
        )

        self.status_label.setStyleSheet(
            """
            QLabel {
                color: #d89b00;
                font-weight: bold;
            }
            """
        )

        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)

        self.thread = QThread()

        self.worker = BluetoothWorker()
        self.worker.moveToThread(self.thread)

        self.thread.started.connect(
            self.worker.run
        )

        self.worker.log_message.connect(
            self.write_log
        )

        self.worker.sensor_values.connect(
            self.on_sensor_values
        )

        self.worker.connected.connect(
            self.on_connected
        )

        self.worker.disconnected.connect(
            self.on_disconnected
        )

        self.worker.error.connect(
            self.on_error
        )

        self.worker.finished.connect(
            self.on_worker_finished
        )

        self.thread.start()

    def stop_bluetooth(self):

        if self.worker is not None:
            self.write_log(
                "Stopping Bluetooth..."
            )

            self.worker.stop()

        self.stop_button.setEnabled(False)

    @Slot(str, str)
    def on_sensor_values(self, red_value, ir_value):

        self.red_value_label.setText(red_value)
        self.ir_value_label.setText(ir_value)
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.last_sample_label.setText(f"Last sample: {timestamp}")

    # -------------------------------------------------------------
    # Worker callbacks
    # -------------------------------------------------------------

    @Slot(str)
    def write_log(self, message):

        timestamp = datetime.now().strftime("%H:%M:%S")

        self.log.appendPlainText(
            f"[{timestamp}] {message}"
        )

        scrollbar = self.log.verticalScrollBar()
        scrollbar.setValue(
            scrollbar.maximum()
        )

    @Slot(str)
    def write_status(self, message):

        self.log.appendPlainText(message)

        scrollbar = self.log.verticalScrollBar()
        scrollbar.setValue(
            scrollbar.maximum()
        )

    @Slot(str)
    def on_connected(self, device_name):

        self.status_label.setText(
            f"● Connected: {device_name}"
        )

        self.status_label.setStyleSheet(
            """
            QLabel {
                color: #19a974;
                font-weight: bold;
            }
            """
        )

        self.write_log(
            f"Connected to {device_name}"
        )

    @Slot()
    def on_disconnected(self):

        self.status_label.setText(
            "● Disconnected"
        )

        self.status_label.setStyleSheet(
            """
            QLabel {
                color: #888;
                font-weight: bold;
            }
            """
        )

    @Slot(str)
    def on_error(self, message):

        self.write_log(
            f"ERROR: {message}"
        )

        self.status_label.setText(
            "● Bluetooth error"
        )

        self.status_label.setStyleSheet(
            """
            QLabel {
                color: #d64545;
                font-weight: bold;
            }
            """
        )

    @Slot()
    def on_worker_finished(self):

        self.write_log(
            "Bluetooth worker stopped."
        )

        self.status_label.setText(
            "● Stopped"
        )

        self.status_label.setStyleSheet(
            """
            QLabel {
                color: #888;
                font-weight: bold;
            }
            """
        )

        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)

        if self.thread is not None:
            self.thread.quit()
            self.thread.wait()

        self.worker = None
        self.thread = None

    # -------------------------------------------------------------
    # Window close
    # -------------------------------------------------------------

    def closeEvent(self, event):

        if self.worker is not None:
            self.worker.stop()

        if self.thread is not None:
            self.thread.quit()
            self.thread.wait()

        event.accept()


def main():

    app = QApplication(sys.argv)

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
