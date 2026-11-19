"""
Virtual Instrument Cluster ECU.

Consumes VehicleSpeedService:
  Calls : GetSpeed, GetVehicleState
  Events: SpeedChanged, OverspeedWarning
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
    CONSUMER_PORT,
    GET_SPEED_METHOD_ID,
    GET_VEHICLE_STATE_METHOD_ID,
    INSTANCE_ID,
    INTERFACE_IP,
    OVERSPEED_WARNING_EVENT_ID,
    SERVICE_ID,
    SPEED_CHANGED_EVENT_ID,
    SpeedPayload,
    VehicleStatePayload,
    overspeed_eventgroup,
    speed_eventgroup,
    state_to_text,
    vehicle_speed_service,
)


def event_callback(
    event_id: int,
    event_payload: bytes,
) -> None:

    try:

        speed = SpeedPayload().deserialize(
            event_payload
        ).speed_kmph.value

        print()

        if event_id == SPEED_CHANGED_EVENT_ID:

            print("SpeedChanged notification received")
            print(f"Event ID      : 0x{event_id:04X}")
            print(f"Payload bytes : {event_payload.hex(' ')}")
            print(f"Vehicle Speed : {speed} km/h")

            if speed == 0:
                print("Vehicle State : STOPPED")

        elif event_id == OVERSPEED_WARNING_EVENT_ID:

            print("OVERSPEED WARNING")
            print(f"Event ID      : 0x{event_id:04X}")
            print(f"Payload bytes : {event_payload.hex(' ')}")
            print(f"Vehicle Speed : {speed} km/h")

        else:

            print(f"Unknown event 0x{event_id:04X}")

    except Exception as error:

        print(f"Could not decode event payload: {error}")


async def call_get_speed(client_instance) -> None:

    print()
    print("Calling GetSpeed...")

    result = await asyncio.wait_for(
        client_instance.call_method(
            GET_SPEED_METHOD_ID,
            b"",
        ),
        timeout=4,
    )

    if (
        result.message_type == MessageType.RESPONSE
        and result.return_code == ReturnCode.E_OK
    ):

        speed = SpeedPayload().deserialize(
            result.payload
        ).speed_kmph.value

        print("GetSpeed response received")
        print(f"Payload bytes : {result.payload.hex(' ')}")
        print(f"Vehicle Speed : {speed} km/h")

    else:

        print(
            f"GetSpeed error: {result.message_type} "
            f"{result.return_code}"
        )


async def call_get_vehicle_state(client_instance) -> None:

    print()
    print("Calling GetVehicleState...")

    result = await asyncio.wait_for(
        client_instance.call_method(
            GET_VEHICLE_STATE_METHOD_ID,
            b"",
        ),
        timeout=4,
    )

    if (
        result.message_type == MessageType.RESPONSE
        and result.return_code == ReturnCode.E_OK
    ):

        state = VehicleStatePayload().deserialize(
            result.payload
        ).state.value

        print("GetVehicleState response received")
        print(f"Payload bytes : {result.payload.hex(' ')}")
        print(f"Vehicle State : {state_to_text(state)}")

    else:

        print(
            f"GetVehicleState error: {result.message_type} "
            f"{result.return_code}"
        )


async def method_loop(client_instance) -> None:

    while True:

        try:

            if not await client_instance.is_available():

                print()
                print("VehicleSpeedService : NOT AVAILABLE")

            else:

                await call_get_speed(client_instance)
                await call_get_vehicle_state(client_instance)

        except Exception as error:

            print(f"Method call failed: {error}")

        await asyncio.sleep(5)


async def main() -> None:

    set_someipy_log_level(logging.INFO)

    print("=" * 60)
    print("Virtual Instrument Cluster ECU")
    print("VehicleSpeedService Consumer")
    print("=" * 60)

    print(f"Required Service ID  : 0x{SERVICE_ID:04X}")
    print(f"Required Instance ID : 0x{INSTANCE_ID:04X}")
    print(f"Consumer endpoint    : {INTERFACE_IP}:{CONSUMER_PORT}")

    print("=" * 60)

    print("Connecting to someipy daemon...")

    daemon = await connect_to_someipy_daemon()

    print("Connected to someipy daemon")

    client_instance = ClientServiceInstance(
        daemon=daemon,
        service=vehicle_speed_service,
        instance_id=INSTANCE_ID,
        endpoint_ip=INTERFACE_IP,
        endpoint_port=CONSUMER_PORT,
    )

    client_instance.register_callback(event_callback)

    print("Searching for VehicleSpeedService...")

    while not await client_instance.is_available():

        print("VehicleSpeedService is not yet available")

        await asyncio.sleep(1)

    print()
    print("VehicleSpeedService is AVAILABLE")

    print("Subscribing to SpeedChanged (group 0x0001)...")
    client_instance.subscribe_eventgroup(speed_eventgroup, 5)

    print("Subscribing to OverspeedWarning (group 0x0002)...")
    client_instance.subscribe_eventgroup(overspeed_eventgroup, 5)

    print("Event-group subscriptions requested")

    method_task = asyncio.create_task(
        method_loop(client_instance)
    )

    try:

        await asyncio.Future()

    finally:

        method_task.cancel()

        try:
            await method_task
        except asyncio.CancelledError:
            pass

        await daemon.disconnect_from_daemon()


if __name__ == "__main__":

    try:
        asyncio.run(main())

    except KeyboardInterrupt:
        print("\nInstrument Cluster stopped")
