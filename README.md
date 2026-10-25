# ESP32 Live Light Monitor

A real-time light monitoring system using an ESP32, an LDR sensor, and a Python desktop application.

### Hardware

* ESP32 DevKit V1
* LDR photoresistor
* 10kΩ resistor

### Wiring

* 3V3 → LDR → GPIO34
* GPIO34 → 10kΩ resistor → GND

### Features

* Live light readings and graph.
* Low, Medium, and Bright light status.
* Minimum and maximum readings.
* Save readings to CSV.

### Software

* ESP32 firmware: C++ (Arduino)
* Desktop app: Python, Tkinter, Matplotlib, and PySerial

### Run

Install dependencies:

```bash
pip install -r requirements.txt
```

Start the application:

```bash
python desktop/app.py
```

Connect the ESP32 via USB, select its COM port, and click **Connect**.

**Note:** Readings represent relative light intensity, not calibrated lux values.
