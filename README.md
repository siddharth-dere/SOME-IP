# 🚗 Virtual Multi-ECU Automotive Network via SOME/IP

![Python](https://img.shields.io/badge/Python-3.12-blue?logo=python&logoColor=white)
![Middleware](https://img.shields.io/badge/Middleware-SOME%2FIP-orange)
![Platform](https://img.shields.io/badge/Platform-Ubuntu%20Linux-lightgrey?logo=ubuntu)
![Framework](https://img.shields.io/badge/Library-someipy%202.1.2-brightgreen)

## 📖 Overview

This project simulates a modern Service-Oriented Architecture (SOA) within a vehicle's network using Python and **SOME/IP** (Scalable service-Oriented MiddlewarE over IP). 

By implementing four distinct virtual Electronic Control Units (ECUs) across localhost, this repository demonstrates how distributed automotive systems communicate, discover services dynamically, and recover from node failures. It extends basic client-server models by introducing multiple service providers, publish-subscribe event streams, multi-service consumers, and application-level payload validation.

---

## 🏗️ System Architecture & Topology

The network relies on a local SOME/IP daemon (`someipyd`) routing UDP traffic over `127.0.0.1`. The architecture showcases two primary SOA concepts:
1. **Multiple consumers utilizing a single service** (Instrument Cluster and Central Display both use `VehicleSpeedService`).
2. **A single consumer aggregating multiple services** (Central Display consumes both `VehicleSpeedService` and `ClimateService`).

```text
                                [ SOME/IP NETWORK ]
                                         │
       +-------------------------+       │       +-------------------------+
       |   ECU 1: Vehicle ECU    |       │       |   ECU 3: Climate ECU    |
       |  (Service Provider 1)   |───────┼───────|  (Service Provider 2)   |
       |   Service ID: 0x1234    |       │       |   Service ID: 0x2234    |
       |      Port: 3000         |       │       |      Port: 3001         |
       +-------------------------+       │       +-------------------------+
                    │                    │                    │
                    └────────────────────┼────────────────────┘
                                         │
               ┌─────────────────────────┴─────────────────────────┐
               ▼                                                   ▼
  +-------------------------+                         +-------------------------+
  | ECU 2: Instrument Clstr |                         | ECU 4: Central Display  |
  |   (Service Consumer)    |                         | (Multi-Service Consumer)|
  |      Port: 3002         |                         |   Ports: 3003 & 3004    |
  +-------------------------+                         +-------------------------+
```

---

## ⚙️ Service Specifications & Data Dictionary

### 1. VehicleSpeedService (Provider: ECU 1)
Handles real-time vehicle telemetry and safety alerts.
* **Service ID:** `0x1234` | **Instance ID:** `0x5678`

| Element Name | Type | ID | Description & Payload Encoding |
| :--- | :---: | :---: | :--- |
| **GetSpeed** | Method | `0x0001` | Returns current speed as `uint16` (in km/h). |
| **GetVehicleState** | Method | `0x0002` | Returns `0` (STOPPED) or `1` (MOVING) as `uint8`. |
| **SpeedChanged** | Event | `0x8001` | Emitted on every speed update. Subscribed via Event Group `0x0001`. |
| **OverspeedWarning** | Event | `0x8002` | Emitted *only* when speed > 80 km/h. Subscribed via Event Group `0x0002`. |

### 2. ClimateService (Provider: ECU 3)
Manages the vehicle's HVAC system, demonstrating application-layer validation and fixed-point decimal encoding.
* **Service ID:** `0x2234` | **Instance ID:** `0x0001`

| Element Name | Type | ID | Description & Payload Encoding |
| :--- | :---: | :---: | :--- |
| **GetCabinTemp** | Method | `0x0001` | Returns temp as `int16` in **tenths of a degree** (e.g., `245` = 24.5°C). |
| **SetTargetTemp** | Method | `0x0002` | Accepts target temp (`int16`). Valid range: `160` to `300` (16.0°C - 30.0°C). Returns status: `0` (Accepted), `1` (Invalid). |
| **CabinTempChanged**| Event | `0x8001` | Emitted upon cabin thermal shifts. Subscribed via Event Group `0x0001`. |

> **Note on Event IDs:** Both services utilize Event ID `0x8001`. The Central Display consumer successfully disambiguates these by inspecting the parent **Service ID** in the SOME/IP message header.

---

## 📂 Repository Structure

```text
someip-python-assignment/
├── src/
│   ├── vehicle_speed_interface.py   # Data types & service definition for Speed
│   ├── vehicle_speed_service.py     # Provider implementation (ECU 1)
│   ├── cluster_client.py            # Consumer implementation (ECU 2)
│   ├── climate_interface.py         # Data types & service definition for Climate
│   ├── climate_service.py           # Provider implementation (ECU 3)
│   └── central_display.py           # Multi-service consumer (ECU 4)
├── config/
│   └── someipyd.json                # Localhost configuration for the SOME/IP daemon
├── captures/
│   └── assignment2-multi-ecu.pcapng # Wireshark network capture of the system
├── requirements.txt                 # Python dependencies
└── README.md
```

---

## 🚀 Installation & Setup

1. **Clone the repository and navigate into it:**
   ```bash
   git clone <your-repo-url>
   cd someip-python-assignment
   ```
2. **Create and activate a virtual environment:**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```
3. **Install required dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

---

## 💻 Running the System (Execution Guide)

To properly observe **SOME/IP Service Discovery (SD)** in action, it is highly recommended to start the consumers *before* the providers. You will need **5 separate terminal windows**.

*Remember to run `source .venv/bin/activate` in every terminal!*

**Step 1: Start the Middleware Daemon (Terminal 1)**
```bash
someipyd --config config/someipyd.json
```

**Step 2: Start the Consumers (Terminals 2 & 3)**
```bash
python src/cluster_client.py
# In next terminal:
python src/central_display.py
```
*Expected Output:* Both applications will report that `VehicleSpeedService` and `ClimateService` are `NOT AVAILABLE`. They are actively listening for SD offers.

**Step 3: Start the Vehicle ECU (Terminal 4)**
```bash
python src/vehicle_speed_service.py
```
*Expected Output:* The consumers will instantly detect `VehicleSpeedService`, mark it `AVAILABLE`, and begin logging speed telemetry (methods and events).

**Step 4: Start the Climate ECU (Terminal 5)**
```bash
python src/climate_service.py
```
*Expected Output:* The Central Display will detect `ClimateService`, mark it `AVAILABLE`, and execute its automated temperature boundary validation sequence.

---

## 🧪 Testing & Demonstrated Scenarios

This repository acts as a testbed for several critical automotive networking scenarios:

*   **Dynamic Service Discovery (SD):** Nodes join and leave the network seamlessly without static IP/Port hardcoding.
*   **Application-Level Validation:** The Climate ECU actively rejects `SetTargetTemperature` requests outside the 16.0°C–30.0°C range, proving that SOME/IP handles transport, but the application dictates logic.
*   **Fault Isolation & Recovery:** 
    *   If you kill the Climate ECU (`Ctrl+C`), the Central Display marks it offline, but continues receiving speed data perfectly.
    *   Restarting the Climate ECU triggers automatic SD re-discovery and re-subscription.
*   **Selective Event Triggering:** The `OverspeedWarning` is an exception-based event. It remains silent during normal operation, saving bandwidth, and only publishes when the >80 km/h threshold is breached.

---

## 🔍 Wireshark Analysis

A pre-recorded packet capture is available at `captures/assignment2-multi-ecu.pcapng`. 

To analyze the traffic yourself:
1. Open Wireshark and listen on the Loopback interface (`lo`).
2. Use the display filter: `someip || someipsd`
3. **Key things to observe:**
   *   **SOME/IP-SD:** Look for `OfferService` (from Providers) and `SubscribeEventgroup` (from Consumers).
   *   **Method Calls:** Differentiate Requests (Message Type `0x00`) and Responses (Message Type `0x80`).
   *   **Event Notifications:** Verify the Message Type is `0x02` (Notification). You can decode the payload by cross-referencing the Service IDs (`0x1234` or `0x2234`).
