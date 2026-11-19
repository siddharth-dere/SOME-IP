"""
Virtual Vehicle ECU.

Provides VehicleSpeedService:
  Methods: GetSpeed, GetVehicleState
  Events : SpeedChanged, OverspeedWarning
"""

import asyncio
import logging
from typing import Tuple

from someipy import (
    MessageType,
    Method,
    MethodResult,
    ReturnCode,
    ServerServiceInstance,
    ServiceBuilder,
    TransportLayerProtocol,
    connect_to_someipy_daemon,
)

from someipy.someipy_logging import set_someipy_log_level

from vehicle_speed_interface import (
    GET_SPEED_METHOD_ID,
    GET_VEHICLE_STATE_METHOD_ID,
    INSTANCE_ID,
    INTERFACE_IP,
    MAJOR_VERSION,
    OVERSPEED_EVENTGROUP_ID,
    OVERSPEED_THRESHOLD_KMPH,
    OVERSPEED_WARNING_EVENT_ID,
    PROVIDER_PORT,
    SERVICE_ID,
    SPEED_CHANGED_EVENT_ID,
    SPEED_EVENTGROUP_ID,
    VEHICLE_STATE_MOVING,
    VEHICLE_STATE_STOPPED,
    SpeedPayload,
    VehicleStatePayload,
    overspeed_eventgroup,
    speed_eventgroup,
    state_to_text,
)


current_speed_kmph = 0


async def get_speed_handler(
    input_data: bytes,
    client_address: Tuple[str, int],
) -> MethodResult:

    print()
    print("GetSpeed request received")
    print(f"Consumer address : {client_address[0]}:{client_address[1]}")
    print(f"Current speed    : {current_speed_kmph} km/h")

    response_payload = SpeedPayload(current_speed_kmph).serialize()

    result = MethodResult()
    result.message_type = MessageType.RESPONSE
    result.return_code = ReturnCode.E_OK
    result.payload = response_payload

    print(f"Response bytes   : {response_payload.hex(' ')}")
    print("GetSpeed response sent")

    return result


async def get_vehicle_state_handler(
    input_data: bytes,
    client_address: Tuple[str, int],
) -> MethodResult:

    if current_speed_kmph == 0:
        state = VEHICLE_STATE_STOPPED
    else:
        state = VEHICLE_STATE_MOVING

    print()
    print("GetVehicleState request received")
    print(f"Consumer address : {client_address[0]}:{client_address[1]}")
    print(f"Current speed    : {current_speed_kmph} km/h")
    print(f"Vehicle state    : {state} ({state_to_text(state)})")

    response_payload = VehicleStatePayload(state).serialize()

    result = MethodResult()
    result.message_type = MessageType.RESPONSE
    result.return_code = ReturnCode.E_OK
    result.payload = response_payload

    print(f"Response bytes   : {response_payload.hex(' ')}")
    print("GetVehicleState response sent")

    return result


def build_provider_service():

    get_speed_method = Method(
        id=GET_SPEED_METHOD_ID,
        protocol=TransportLayerProtocol.UDP,
        method_handler=get_speed_handler,
    )

    get_vehicle_state_method = Method(
        id=GET_VEHICLE_STATE_METHOD_ID,
        protocol=TransportLayerProtocol.UDP,
        method_handler=get_vehicle_state_handler,
    )

    return (
        ServiceBuilder()
        .with_service_id(SERVICE_ID)
        .with_major_version(MAJOR_VERSION)
        .with_method(get_speed_method)
        .with_method(get_vehicle_state_method)
        .with_eventgroup(speed_eventgroup)
        .with_eventgroup(overspeed_eventgroup)
        .build()
    )


async def simulate_speed(
    service_instance: ServerServiceInstance,
) -> None:

    global current_speed_kmph

    while True:

        current_speed_kmph += 10

        if current_speed_kmph > 100:
            current_speed_kmph = 0

        event_payload = SpeedPayload(
            current_speed_kmph
        ).serialize()

        print()
        print(
            f"Simulated speed changed to "
            f"{current_speed_kmph} km/h"
        )

        # SpeedChanged is always sent
        service_instance.send_event(
            SPEED_EVENTGROUP_ID,
            SPEED_CHANGED_EVENT_ID,
            event_payload,
        )

        print("SpeedChanged event sent")

        # OverspeedWarning only when speed > 80 km/h
        if current_speed_kmph > OVERSPEED_THRESHOLD_KMPH:

            service_instance.send_event(
                OVERSPEED_EVENTGROUP_ID,
                OVERSPEED_WARNING_EVENT_ID,
                event_payload,
            )

            print(
                f"OverspeedWarning event sent "
                f"({current_speed_kmph} km/h > "
                f"{OVERSPEED_THRESHOLD_KMPH} km/h)"
            )

        else:

            print("No OverspeedWarning (speed not above 80 km/h)")

        await asyncio.sleep(2)


async def main() -> None:

    set_someipy_log_level(logging.INFO)

    print("=" * 60)
    print("Virtual Vehicle ECU")
    print("VehicleSpeedService Provider")
    print("=" * 60)

    print(f"Service ID        : 0x{SERVICE_ID:04X}")
    print(f"Instance ID       : 0x{INSTANCE_ID:04X}")
    print(f"GetSpeed          : 0x{GET_SPEED_METHOD_ID:04X}")
    print(f"GetVehicleState   : 0x{GET_VEHICLE_STATE_METHOD_ID:04X}")
    print(
        f"SpeedChanged      : 0x{SPEED_CHANGED_EVENT_ID:04X} "
        f"(group 0x{SPEED_EVENTGROUP_ID:04X})"
    )
    print(
        f"OverspeedWarning  : 0x{OVERSPEED_WARNING_EVENT_ID:04X} "
        f"(group 0x{OVERSPEED_EVENTGROUP_ID:04X})"
    )
    print(f"Provider endpoint : {INTERFACE_IP}:{PROVIDER_PORT}")

    print("=" * 60)

    print("Connecting to someipy daemon...")

    daemon = await connect_to_someipy_daemon()

    print("Connected to someipy daemon")

    provider_service = build_provider_service()

    provider_instance = ServerServiceInstance(
        daemon=daemon,
        service=provider_service,
        instance_id=INSTANCE_ID,
        endpoint_ip=INTERFACE_IP,
        endpoint_port=PROVIDER_PORT,
        ttl=5,
        cyclic_offer_delay_ms=2000,
    )

    print("Offering VehicleSpeedService...")

    await provider_instance.start_offer()

    print("VehicleSpeedService is being offered")

    speed_task = asyncio.create_task(
        simulate_speed(provider_instance)
    )

    try:

        await asyncio.Future()

    finally:

        speed_task.cancel()

        try:
            await speed_task
        except asyncio.CancelledError:
            pass

        await provider_instance.stop_offer()

        await daemon.disconnect_from_daemon()


if __name__ == "__main__":

    try:
        asyncio.run(main())

    except KeyboardInterrupt:
        print("\nVehicle Speed Service stopped")
