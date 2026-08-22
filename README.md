# HealthTracker

Open source wearable tracker designed to help keep track of your health.

> ⚠️ **Very early development:** HealthTracker is **not finished and is not currently being tested as a working device**. I am still designing the first hardware revision.

The current focus is **Revision 1 (Rev 1)**. This board is being designed specifically to give me a platform for debugging the hardware, testing the individual chips, and developing the actual firmware.

Once Rev 1 is manufactured and assembled, the next stage will be hardware bring-up and testing. That means verifying power, communication buses, sensors, the MCU, Bluetooth LE, and everything else before moving further into firmware development.

## Hardware

### Main MCU

* **nRF54L15-QFxx** | Nordic | MCU + Bluetooth LE

### Sensors

* **MAX30102** | Analog Devices / Maxim | Heart rate + SpO₂
* **MAX30205** | Analog Devices / Maxim | Body temperature
* **ICM-42605** | TDK InvenSense | 6-axis IMU, accelerometer + gyroscope
* **MAX30003** | Analog Devices / Maxim | Single-channel ECG

### Planned interfaces

* **USB-C** | Programming, development, and power -Will be removed in the final revisions and will be replaced with pogo magnetic charging on a small puck you slide on
* **External I²C connector** | Additional sensors and modules -Maybe

### Currently removed

* ~~**ICS-41350**~~ | Microphone
* ~~**LTR-303ALS-01**~~ | Ambient light sensor 
Too niche maybe one day

## Development Status

**Current stage: Rev 1 hardware design**

The project is currently in the hardware design phase. I am designing the first PCB revision with debugging, hardware testing, and firmware development in mind.

The development path currently looks roughly like:

1. **Design Rev 1 PCB**
2. Manufacture and assemble Rev 1
3. **Hardware bring-up and debugging**
4. Test the MCU and individual sensors
5. Develop the initial firmware
6. Debug and iterate on the hardware and firmware
7. Build future hardware revisions based on what Rev 1 teaches us

The design is expected to change significantly during development. Components may be replaced, removed, or added as testing reveals what actually works.

The goal is to eventually create an open source wearable health tracker with open hardware and firmware, but **that finished device does not exist yet**. This repository documents the development process as the project works toward it.

**This is not a medical device and should not be relied upon for medical decisions.**

Expected release hopefully before 2027 (faster if i get some help :) )
