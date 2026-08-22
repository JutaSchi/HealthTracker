# HealthTracker

> ⚠️ **Very early development:** HealthTracker is **not finished and is not currently being tested as a working device**. I am still designing the first hardware revision.

The current focus is **Revision 1 (Rev 1)**. This board is being designed specifically to give me a platform for debugging the hardware, testing the individual chips, and developing the actual firmware.

Once Rev 1 is manufactured and assembled, the next stage will be hardware bring-up and testing. This includes verifying power, communication buses, sensors, the MCU, Bluetooth LE, and everything else before moving further into firmware development.

## Hardware

### Main MCU

* **nRF54L15-QFxx** | Nordic | MCU + Bluetooth LE

### Sensors

* **MAX30102** | Analog Devices / Maxim | Heart rate + SpO₂
* **MAX30205** | Analog Devices / Maxim | Body temperature
* **ICM-42605** | TDK InvenSense | 6-axis IMU, accelerometer + gyroscope
* **MAX30003** | Analog Devices / Maxim | Single-channel ECG

### Planned interfaces

* **USB-C** | Programming, development, and power

  * Planned for Rev 1 and early development.
  * Intended to be removed in a future revision and replaced with **magnetic pogo-pin charging** using a small charging puck.
* **External I²C connector** | Additional sensors and modules

  * Currently planned, but this may change depending on the final design.

### Currently removed

* ~~**ICS-41350**~~ | Microphone
* ~~**LTR-303ALS-01**~~ | Ambient light sensor

  * Currently removed because it is a little too niche for the current design. It may return in a future revision.

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
7. Build future hardware revisions based on what Rev 1 teaches me

The design is expected to change significantly during development. Components may be replaced, removed, or added as testing reveals what actually works.

The goal is to eventually create an open source wearable health tracker with open hardware and firmware, but **that finished device does not exist yet**. This repository documents the development process as the project works toward it.

> **This is not a medical device and should not be relied upon for medical decisions.**

### Expected release

**Target: hopefully before 2027.**

Development may move faster with additional help, feedback, testing, and funding.

## ❤️ Support HealthTracker

I'm 17 and still in school, so hardware development is being done alongside everything else that comes with being a student.

If you want to support HealthTracker, donations can help fund:

* 🔧 Prototype PCBs
* 🧩 Components and sensors
* 🧪 Hardware testing
* 🔄 Future PCB revisions
* 💻 Development hardware

### 🪙 Monero (XMR)

```text
89cXGnXbwSa9bbsy4fhWJDDKPyL9iLzSA1rdJNzLymCy4uoH98UMi1CLKgf816oXGy5TqjzJHf3Tqbkuuz5kRKtSPPTLEZD
```

More ways to support the project will be added soon.

I believe in **decentralized and open-source payment methods**, and I want HealthTracker to remain as open and accessible as possible.

Thanks for checking out the project and following along with the development.-Julian

*Made with ❤️ in the Nordics*
