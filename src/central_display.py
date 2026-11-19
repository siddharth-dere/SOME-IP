"""
Central Display ECU - SOME/IP Assignment 2.

Consumes:
    VehicleSpeedService
    ClimateService
"""

import asyncio
import logging

from someipy import (
    ClientServiceInstance,
    MessageType,
    ReturnCode,
    connect_to_someipy_daemon,
)
from someipy.someipy_logging import set_someipy_log_level

from vehicle_speed_interface import (
    INSTANCE_ID,
    INTERFACE_IP,
    DISPLAY_VEHICLE_PORT,
    GET_SPEED_METHOD_ID,
    GET_VEHICLE_STATE_METHOD_ID,
    SPEED_CHANGED_EVENT_ID,
    OVERSPEED_WARNING_EVENT_ID,
    SpeedPayload,
    VehicleStatePayload,
    speed_eventgroup,
    overspeed_eventgroup,
    state_to_text,
    vehicle_speed_service,
)

from climate_interface import (
    CLIMATE_INSTANCE_ID,
    CLIMATE_INTERFACE_IP,
    DISPLAY_CLIMATE_PORT,
    GET_CABIN_TEMPERATURE_METHOD_ID,
    SET_TARGET_TEMPERATURE_METHOD_ID,
    CABIN_TEMPERATURE_CHANGED_EVENT_ID,
    CabinTemperaturePayload,
    TargetTemperaturePayload,
    SetTargetStatusPayload,
    climate_eventgroup,
    climate_service,
    temp_to_text,
    status_to_text,
)


# Vehicle event callback
def vehicle_event_callback(event_id, payload):
    try:
        speed = SpeedPayload().deserialize(
            payload
        ).speed_kmph.value

        if event_id == SPEED_CHANGED_EVENT_ID:
            print(f"\n[VEHICLE EVENT] Speed Updated: {speed} km/h")

        elif event_id == OVERSPEED_WARNING_EVENT_ID:
            print(f"\n[VEHICLE WARNING] OVERSPEED: {speed} km/h")

    except Exception as error:
        print("Vehicle event error:", error)


# Climate event callback
def climate_event_callback(event_id, payload):
    try:
        if event_id == CABIN_TEMPERATURE_CHANGED_EVENT_ID:
            temperature = CabinTemperaturePayload().deserialize(
                payload
            ).temperature.value

            print(
                "\n[CLIMATE EVENT] Cabin Temperature Updated:",
                temp_to_text(temperature),
            )

    except Exception as error:
        print("Climate event error:", error)


# Common SOME/IP method request helper
async def request_method(client, method_id, payload=b""):
    result = await asyncio.wait_for(
        client.call_method(method_id, payload),
        timeout=4,
    )

    if (
        result.message_type == MessageType.RESPONSE
        and result.return_code == ReturnCode.E_OK
    ):
        return result.payload

    print(
        f"Method 0x{method_id:04X} failed:",
        result.message_type,
        result.return_code,
    )
    return None


# Monitor VehicleSpeedService independently
async def vehicle_loop(client):
    previous_availability = None

    while True:
        try:
            available = await client.is_available()

            if available != previous_availability:
                print(
                    "\nVehicleSpeedService:",
                    "AVAILABLE" if available else "NOT AVAILABLE",
                )

                if available:
                    client.subscribe_eventgroup(speed_eventgroup, 5)
                    client.subscribe_eventgroup(overspeed_eventgroup, 5)
                    print("Vehicle event subscriptions requested")

            previous_availability = available

            if available:
                payload = await request_method(
                    client, GET_SPEED_METHOD_ID
                )

                if payload is not None:
                    speed = SpeedPayload().deserialize(
                        payload
                    ).speed_kmph.value

                    print(f"[VEHICLE] Speed: {speed} km/h")

                payload = await request_method(
                    client, GET_VEHICLE_STATE_METHOD_ID
                )

                if payload is not None:
                    state = VehicleStatePayload().deserialize(
                        payload
                    ).state.value

                    print(
                        "[VEHICLE] State:",
                        state_to_text(state),
                    )

        except Exception as error:
            print("[VEHICLE] Communication error:", repr(error))

        await asyncio.sleep(5)


# Monitor ClimateService independently
async def climate_loop(client):
    previous_availability = None

    # Assignment 2 temperature validation tests:
    # 22.0, 16.0, 30.0, 10.0 and 35.0 degrees Celsius.
    test_temperatures = [220, 160, 300, 100, 350]
    test_index = 0

    while True:
        try:
            available = await client.is_available()

            if available != previous_availability:
                print(
                    "\nClimateService:",
                    "AVAILABLE" if available else "NOT AVAILABLE",
                )

                if available:
                    client.subscribe_eventgroup(climate_eventgroup, 5)
                    print("Climate event subscription requested")
                    test_index = 0

            previous_availability = available

            if available:
                payload = await request_method(
                    client, GET_CABIN_TEMPERATURE_METHOD_ID
                )

                if payload is not None:
                    temperature = CabinTemperaturePayload().deserialize(
                        payload
                    ).temperature.value

                    print(
                        "[CLIMATE] Cabin Temperature:",
                        temp_to_text(temperature),
                    )

                # Send each assignment validation test once.
                if test_index < len(test_temperatures):
                    target = test_temperatures[test_index]

                    print(
                        "[CLIMATE] Requesting Target:",
                        temp_to_text(target),
                    )

                    payload = await request_method(
                        client,
                        SET_TARGET_TEMPERATURE_METHOD_ID,
                        TargetTemperaturePayload(target).serialize(),
                    )

                    if payload is not None:
                        status = SetTargetStatusPayload().deserialize(
                            payload
                        ).status.value

                        print(
                            "[CLIMATE] SetTargetTemperature:",
                            status_to_text(status),
                        )

                        test_index += 1

        except Exception as error:
            print("[CLIMATE] Communication error:", repr(error))

        await asyncio.sleep(5)


async def main():
    set_someipy_log_level(logging.INFO)

    print("=" * 55)
    print("CENTRAL VEHICLE DISPLAY")
    print("SOME/IP Multi-Service Consumer")
    print("=" * 55)

    print("Connecting to SOME/IP daemon...")
    daemon = await connect_to_someipy_daemon()
    print("Connected to SOME/IP daemon")

    # Client 1: VehicleSpeedService
    vehicle_client = ClientServiceInstance(
        daemon=daemon,
        service=vehicle_speed_service,
        instance_id=INSTANCE_ID,
        endpoint_ip=INTERFACE_IP,
        endpoint_port=DISPLAY_VEHICLE_PORT,
    )

    # Client 2: ClimateService
    climate_client = ClientServiceInstance(
        daemon=daemon,
        service=climate_service,
        instance_id=CLIMATE_INSTANCE_ID,
        endpoint_ip=CLIMATE_INTERFACE_IP,
        endpoint_port=DISPLAY_CLIMATE_PORT,
    )

    vehicle_client.register_callback(vehicle_event_callback)
    climate_client.register_callback(climate_event_callback)

    print("Vehicle client endpoint: 127.0.0.1:3003")
    print("Climate client endpoint: 127.0.0.1:3004")
    print("Monitoring both services independently...")

    tasks = [
        asyncio.create_task(vehicle_loop(vehicle_client)),
        asyncio.create_task(climate_loop(climate_client)),
    ]

    try:
        await asyncio.gather(*tasks)

    finally:
        for task in tasks:
            task.cancel()

        await asyncio.gather(*tasks, return_exceptions=True)
        await daemon.disconnect_from_daemon()


if __name__ == "__main__":
    try:
        asyncio.run(main())

    except KeyboardInterrupt:
        print("\nCentral Display stopped")
