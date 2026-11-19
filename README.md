# SOME/IP Multi-ECU Vehicle Communication System

## Overview

This project demonstrates service-oriented automotive communication using Python and SOME/IP (Scalable service-Oriented MiddlewarE over IP).

It implements four virtual Electronic Control Units (ECUs) communicating through two independent SOME/IP services.

This project extends Assignment 1 by introducing additional methods, events, a ClimateService, multiple service consumers, and fault recovery.

## System Architecture

```text
             +-------------------+
             |    Vehicle ECU    |
             | Service ID 0x1234 |
             |    Port 3000      |
             +---------+---------+
                       |
              +--------+--------+
              |                 |
              v                 v
     +----------------+  +------------------+
     | Instrument     |  | Central Display  |
     | Cluster        |  |                  |
     | Port 3002      |  | Ports 3003,3004  |
     +----------------+  +--------+---------+
                                  ^
                                  |
                        +---------+---------+
                        |    Climate ECU    |
                        | Service ID 0x2234 |
                        |    Port 3001      |
                        +-------------------+
```

All applications communicate using localhost (127.0.0.1).

## Technologies

- Python 3.12
- someipy 2.1.2
- SOME/IP
- SOME/IP Service Discovery
- UDP
- asyncio
- Wireshark
- Ubuntu Linux

## VehicleSpeedService

Service ID: `0x1234`  
Instance ID: `0x5678`  
Provider Port: `3000`

| Element | ID | Type |
|---|---|---|
| GetSpeed | 0x0001 | Method |
| GetVehicleState | 0x0002 | Method |
| SpeedChanged | 0x8001 | Event |
| OverspeedWarning | 0x8002 | Event |

The Vehicle ECU simulates speeds from 0 to 100 km/h.

Vehicle state:
- 0 = STOPPED
- 1 = MOVING

An OverspeedWarning is generated when speed exceeds 80 km/h.

## ClimateService

Service ID: `0x2234`  
Instance ID: `0x0001`  
Provider Port: `3001`

| Element | ID | Type |
|---|---|---|
| GetCabinTemperature | 0x0001 | Method |
| SetTargetTemperature | 0x0002 | Method |
| CabinTemperatureChanged | 0x8001 | Event |

Cabin temperatures are represented as signed 16-bit integers in tenths of a degree Celsius.

The valid target temperature range is 16.0°C to 30.0°C.

Invalid temperature requests are rejected without changing the previously accepted target.

## Project Structure

```text
someip-python-assignment/
├── src/
│   ├── vehicle_speed_interface.py
│   ├── vehicle_speed_service.py
│   ├── cluster_client.py
│   ├── climate_interface.py
│   ├── climate_service.py
│   └── central_display.py
├── config/
│   └── someipyd.json
├── captures/
│   └── assignment2-multi-ecu.pcapng
├── README.md
├── requirements.txt
└── .gitignore
```

## Installation

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Running the System

Open five terminals.

Activate the virtual environment in each terminal:

```bash
source .venv/bin/activate
```

Terminal 1 - SOME/IP Daemon:

```bash
someipyd --config config/someipyd.json
```

Terminal 2 - Vehicle ECU:

```bash
python src/vehicle_speed_service.py
```

Terminal 3 - Climate ECU:

```bash
python src/climate_service.py
```

Terminal 4 - Instrument Cluster:

```bash
python src/cluster_client.py
```

Terminal 5 - Central Display:

```bash
python src/central_display.py
```

Press Ctrl+C to stop each application.

## Features

- Dynamic SOME/IP Service Discovery
- Request-response method communication
- Publish-subscribe event communication
- Multiple consumers of one service
- One consumer accessing multiple services
- Vehicle speed and state monitoring
- Overspeed warnings
- Cabin temperature monitoring
- Target temperature validation
- Independent service availability monitoring
- Recovery after service provider restarts

## Testing

The following scenarios were tested:

1. Vehicle speed and state communication.
2. SpeedChanged and OverspeedWarning reception.
3. Cabin temperature method communication.
4. Target temperature acceptance and rejection.
5. Multiple consumers accessing VehicleSpeedService.
6. Central Display consuming both services.
7. Dynamic Service Discovery.
8. Climate ECU failure and recovery.
9. Vehicle ECU failure and recovery.
10. SOME/IP packet inspection with Wireshark.

## Wireshark Analysis

Capture file:

`captures/assignment2-multi-ecu.pcapng`

Verified packet observations:

- SOME/IP Service Discovery traffic.
- VehicleSpeedService OfferService.
- ClimateService OfferService.
- GetSpeed request and response.
- Matching Session IDs.
- GetSpeed payload decoding (70 km/h).
- GetVehicleState response.

Application logs confirmed event reception, but corresponding event notification packets were not independently identified in Wireshark.

## Learning Outcomes

This project demonstrates service-oriented automotive communication using methods, events, Service Discovery, multiple ECU applications, asynchronous programming, and fault recovery.
