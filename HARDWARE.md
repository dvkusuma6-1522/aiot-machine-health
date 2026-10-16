# Environmental Monitoring Edge Node: Hardware & Electrical Interface Manual

**System:** AI-Powered Multi-Sensor Environmental Monitoring and Prediction System  
**Target Microcontroller:** ESP32 DevKit v1 (30-pin or 36-pin, ESP-WROOM-32)  
**Document Revision:** 1.0 (Production & Viva Reference)  

---

## 1. Master Hardware Pin Mapping

The environmental node interfaces with four physical sensors using dedicated GPIO pins chosen specifically to avoid boot strapping conflicts and peripheral resource collisions:

| Sensor Module | Sensor Pin | ESP32 GPIO | Electrical Domain | Signal Type | Notes & Protection |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **DHT22 (AM2302)** | `VCC` | `3.3V` Rail | 3.3V DC | Power | Requires 100nF decoupling capacitor |
| | `GND` | `GND` Rail | 0V | Ground | Common system ground |
| | `DATA` | **GPIO 4** | 3.3V CMOS | Bi-directional Single-Bus | Requires $4.7\,\text{k}\Omega - 10\,\text{k}\Omega$ pull-up to 3.3V |
| **MQ135 Gas Sensor** | `VCC` | `5.0V` Rail | 5.0V DC | Power | Internal heater requires ~160mA at 5V |
| | `GND` | `GND` Rail | 0V | Ground | Common system ground |
| | `AOUT` | **GPIO 34 (ADC1_CH6)** | Analog ($0.0 - 3.3\text{V}$) | Analog Voltage | **Input-Only Pin**. Filtered with $0.1\mu\text{F}$ capacitor |
| **IR Obstacle Sensor**| `VCC` | `3.3V` Rail | 3.3V DC | Power | Typical consumption 15–20mA |
| | `GND` | `GND` Rail | 0V | Ground | Common system ground |
| | `OUT` | **GPIO 27** | 3.3V CMOS | Digital Input (Active Low) | Software debounced (50ms lockout window) |
| **HC-SR04 Ultrasonic**| `VCC` | `5.0V` Rail | 5.0V DC | Power | Ultrasonic transducer requires 5V for range |
| | `GND` | `GND` Rail | 0V | Ground | Common system ground |
| | `TRIG` | **GPIO 5** | 3.3V CMOS | Digital Output | Directly drives HC-SR04 ($V_{IH} \ge 2.0\text{V}$) |
| | `ECHO` | **GPIO 18** | **3.33V (Divided)** | Digital Input | **CRITICAL: Driven via 1kΩ / 2kΩ Resistor Divider** |

---

## 2. Resistor Voltage Divider Engineering & Calculations

### Why a Voltage Divider is Mandatory
The HC-SR04 ultrasonic distance sensor operates strictly from a $5.0\,\text{V}$ supply rail. When an ultrasonic burst reflects back, its `ECHO` pin drives a digital pulse at the full $5.0\,\text{V}$ rail potential.

> [!CAUTION]
> **ESP32 Silicon Overvoltage Limit:**
> ESP32 GPIO pins are fabricated on a 40nm CMOS process with a maximum rated voltage $V_{DD} + 0.3\,\text{V} = 3.6\,\text{V}$. Connecting a 5.0V `ECHO` line directly to GPIO 18 forward-biases the internal ESD protection diodes, injecting continuous current into the internal 3.3V silicon substrate, leading to thermal breakdown and permanent microcontroller destruction.

### Circuit Diagram

```
HC-SR04 ECHO (5.0V)
       |
      [R1] = 1.0 kΩ (1/4W, 1% metal film)
       |
       +-----> To ESP32 GPIO 18 (Measured: 3.33V)
       |
      [R2] = 2.0 kΩ (1/4W, 1% metal film, or two 1kΩ in series)
       |
   Common GND (0V)
```

### Mathematical Derivation
Using the standard voltage divider equation:
$$V_{\text{out}} = V_{\text{in}} \times \left( \frac{R_2}{R_1 + R_2} \right)$$

Substituting nominal design values:
$$V_{\text{out}} = 5.0\,\text{V} \times \left( \frac{2000\,\Omega}{1000\,\Omega + 2000\,\Omega} \right) = 5.0\,\text{V} \times \frac{2}{3} = 3.333\,\text{V}$$

### Tolerance & Boundary Analysis
Assuming standard $\pm 5\%$ carbon film resistors in worst-case tolerance combinations:
- Worst-case maximum $V_{\text{out}}$ occurs when $R_1$ is at minimum (-5% = $950\,\Omega$) and $R_2$ is at maximum (+5% = $2100\,\Omega$):
  $$V_{\text{out, max}} = 5.25\,\text{V} \times \left( \frac{2100}{950 + 2100} \right) = 5.25\,\text{V} \times 0.6885 = 3.61\,\text{V}$$
- This satisfies the ESP32 absolute upper limit ($3.6\,\text{V}$). For production safety, **1% metal film resistors** are strongly recommended, yielding $V_{\text{out}} \in [3.30\,\text{V}, 3.36\,\text{V}]$.

### Logic Threshold Compatibility
- ESP32 Input High Threshold ($V_{IH}$): $0.75 \times V_{DD} = 0.75 \times 3.3\,\text{V} = 2.475\,\text{V}$.
- Since $3.33\,\text{V} \gg 2.475\,\text{V}$, the pulse is reliably and cleanly registered as a logic `HIGH`.
- Divider current draw: $I = \frac{5.0\,\text{V}}{3000\,\Omega} \approx 1.67\,\text{mA}$, which is well within the HC-SR04 output drive capability ($20\,\text{mA}$).

---

## 3. Peripheral Isolation: Why GPIO 34 (ADC1) was Chosen

A common failure mode in ESP32 IoT projects is erratic ADC readings when Wi-Fi is transmitting.

The ESP32 features two separate Analog-to-Digital Converter modules:
- **ADC2** (shared with GPIO 0, 2, 4, 12, 13, 14, 15, 25, 26, 27). **ADC2 is used internally by the Wi-Fi driver.** Attempting to read analog sensors on ADC2 pins while Wi-Fi is connected results in `ESP_ERR_TIMEOUT` or erroneous $0\,\text{V}$ readings.
- **ADC1** (GPIO 32, 33, 34, 35, 36, 39). **ADC1 is completely independent of the Wi-Fi subsystem.**

By routing the MQ135 analog voltage to **GPIO 34 (ADC1 Channel 6)**, the environmental node guarantees 100% reliable, glitch-free analog sampling concurrently with high-frequency HTTP Wi-Fi telemetry uploads.

---

## 4. Power Architecture & Current Budget

The complete multi-sensor node combines digital and high-current analog heating elements:

| Component | Rail | Typical Current | Peak / Inrush Current | Function / Load Behavior |
| :--- | :--- | :--- | :--- | :--- |
| **ESP32 MCU** | 3.3V (via on-board LDO) | 80 mA | 260 mA | Peaks during 802.11 b/g/n RF packet transmission |
| **MQ135 Gas Sensor** | 5.0V | 150 mA | 180 mA | Continuous heating coil ($R_H \approx 31\,\Omega \pm 3\,\Omega$) |
| **DHT22 Temperature** | 3.3V | 1.0 mA | 1.5 mA | Active sampling every 2 seconds |
| **IR Optical Counter**| 3.3V | 15 mA | 20 mA | Constant infrared LED illumination |
| **HC-SR04 Ultrasonic**| 5.0V | 15 mA | 20 mA | 40 kHz burst pulse transmission |
| **Total Node Budget** | **5.0V Supply** | **~260 mA** | **~480 mA** | |

### Power Supply Recommendation
- **Minimum Requirement:** 5.0V DC regulated supply capable of **1.0A continuous** (USB 3.0 port or 5V 2A external DC power adapter).
- **Decoupling Capacitors:**
  - Place a **$470\,\mu\text{F}$ electrolytic capacitor** across the 5V and GND rail on the breadboard to buffer transient current drops when the ESP32 Wi-Fi radio powers on.
  - Place a **$0.1\,\mu\text{F}$ ceramic capacitor** directly across the MQ135 analog output and ground to suppress high-frequency radio frequency noise.

---

## 5. Thermal Management & MQ135 Heater Isolation

The MQ135 utilizes an internal tin dioxide ($SnO_2$) ceramic heating element to reach operating temperature (~300°C internally, surface temperature ~50°C).

> [!WARNING]
> **Thermal Proximity Interference:**
> If the MQ135 sensor is positioned within 3 cm of the DHT22 temperature sensor, radiant heat from the MQ135 casing will artificially elevate DHT22 temperature readings by $+2^\circ\text{C}$ to $+4^\circ\text{C}$ and depress relative humidity.
> **Required Physical Placement:** Maintain a minimum separation of **8 cm (3.1 inches)** between the MQ135 gas sensor and the DHT22 probe on the breadboard or enclosure.

---

## 6. Complete Breadboard Wiring Guide

```
+========================================================================+
|                        ESP32 DevKit Wiring Map                         |
+========================================================================+
|                                                                        |
|  [5V Power Supply] ----+----------------------------------------+      |
|                        |                                        |      |
|                        +--> MQ135 VCC (Pin 1)                   |      |
|                        +--> HC-SR04 VCC (Pin 1)                 |      |
|                        +--> ESP32 VIN (Pin 19 / 30)             |      |
|                                                                        |
|  [Common GND] ---------+----------------------------------------+      |
|                        |                                        |      |
|                        +--> ESP32 GND                           |      |
|                        +--> MQ135 GND                           |      |
|                        +--> DHT22 GND                           |      |
|                        +--> IR Sensor GND                       |      |
|                        +--> HC-SR04 GND                         |      |
|                        +--> Resistor R2 (2kΩ) Bottom Terminal   |      |
|                                                                        |
|  [3.3V Rail (from ESP32 3V3 Pin)]                                      |
|                        |                                        |      |
|                        +--> DHT22 VCC (Pin 1)                   |      |
|                        +--> DHT22 Pull-up Resistor (4.7kΩ)      |      |
|                        +--> IR Sensor VCC (Pin 1)               |      |
|                                                                        |
|  [Signal Connections]                                                  |
|  - DHT22 DATA (Pin 2)  -------------> ESP32 GPIO 4                     |
|  - MQ135 AOUT (Pin 4)  -------------> ESP32 GPIO 34 (ADC1_CH6)         |
|  - IR Sensor OUT       -------------> ESP32 GPIO 27                    |
|  - HC-SR04 TRIG        -------------> ESP32 GPIO 5                     |
|  - HC-SR04 ECHO        ---> [R1: 1kΩ] --->+---> ESP32 GPIO 18          |
|                                            |                           |
|                                         [R2: 2kΩ]                      |
|                                            |                           |
|                                           GND                          |
+========================================================================+
```
