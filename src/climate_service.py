"""
Virtual Climate ECU - SOME/IP Assignment 2.

Provides:
    GetCabinTemperature()
    SetTargetTemperature()
    CabinTemperatureChanged event
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

from climate_interface import (
    CLIMATE_SERVICE_ID,
    CLIMATE_INSTANCE_ID,
    CLIMATE_MAJOR_VERSION,
    CLIMATE_INTERFACE_IP,
    CLIMATE_PROVIDER_PORT,
    GET_CABIN_TEMPERATURE_METHOD_ID,
    SET_TARGET_TEMPERATURE_METHOD_ID,
    CABIN_TEMPERATURE_CHANGED_EVENT_ID,
    CLIMATE_EVENTGROUP_ID,
    MIN_TARGET_TEMPERATURE,
    MAX_TARGET_TEMPERATURE,
    STATUS_ACCEPTED,
    STATUS_INVALID_TEMPERATURE,
    CabinTemperaturePayload,
    TargetTemperaturePayload,
    SetTargetStatusPayload,
    climate_eventgroup,
    temp_to_text,
    status_to_text,
)


# Initial Climate ECU state
current_cabin_temperature = 240  # 24.0 Celsius
target_temperature = 220         # 22.0 Celsius


def create_response(payload: bytes) -> MethodResult:
    result = MethodResult()
    result.message_type = MessageType.RESPONSE
    result.return_code = ReturnCode.E_OK
    result.payload = payload
    return result


# Method 1: GetCabinTemperature
async def get_cabin_temperature_handler(
    input_data: bytes,
    client_address: Tuple[str, int],
) -> MethodResult:

    print("\nGetCabinTemperature request received")
    print(f"Consumer: {client_address}")
    print(
        "Current Cabin Temperature:",
        temp_to_text(current_cabin_temperature)
    )

    payload = CabinTemperaturePayload(
        current_cabin_temperature
    ).serialize()

    return create_response(payload)


# Method 2: SetTargetTemperature
async def set_target_temperature_handler(
    input_data: bytes,
    client_address: Tuple[str, int],
) -> MethodResult:

    global target_temperature

    print("\nSetTargetTemperature request received")
    print(f"Consumer: {client_address}")

    try:
        request = TargetTemperaturePayload().deserialize(
            input_data
        )
        requested_temperature = request.temperature.value

        print(
            "Requested Target:",
            temp_to_text(requested_temperature)
        )

        if (
            MIN_TARGET_TEMPERATURE
            <= requested_temperature
            <= MAX_TARGET_TEMPERATURE
        ):
            target_temperature = requested_temperature
            status = STATUS_ACCEPTED

            print("Target temperature updated")

        else:
            status = STATUS_INVALID_TEMPERATURE

            print("Invalid temperature request")
            print("Previous target temperature retained")

    except Exception as error:
        print("Invalid request payload:", error)
        status = STATUS_INVALID_TEMPERATURE

    print("Response:", status_to_text(status))
    print(
        "Current Target:",
        temp_to_text(target_temperature)
    )

    payload = SetTargetStatusPayload(status).serialize()

    return create_response(payload)


# Build the provider's ClimateService
def build_climate_provider():

    get_temperature_method = Method(
        id=GET_CABIN_TEMPERATURE_METHOD_ID,
        protocol=TransportLayerProtocol.UDP,
        method_handler=get_cabin_temperature_handler,
    )

    set_temperature_method = Method(
        id=SET_TARGET_TEMPERATURE_METHOD_ID,
        protocol=TransportLayerProtocol.UDP,
        method_handler=set_target_temperature_handler,
    )

    return (
        ServiceBuilder()
        .with_service_id(CLIMATE_SERVICE_ID)
        .with_major_version(CLIMATE_MAJOR_VERSION)
        .with_method(get_temperature_method)
        .with_method(set_temperature_method)
        .with_eventgroup(climate_eventgroup)
        .build()
    )


# Simulate cabin temperature changes
async def simulate_cabin_temperature(
    service_instance: ServerServiceInstance,
):

    global current_cabin_temperature

    temperature_sequence = [
        240,  # 24.0 C
        245,  # 24.5 C
        250,  # 25.0 C
        255,  # 25.5 C
        260,  # 26.0 C
    ]

    index = 0

    while True:

        await asyncio.sleep(2)

        index = (index + 1) % len(temperature_sequence)

        current_cabin_temperature = temperature_sequence[index]

        print()
        print(
            "Cabin Temperature Changed:",
            temp_to_text(current_cabin_temperature)
        )

        payload = CabinTemperaturePayload(
            current_cabin_temperature
        ).serialize()

        service_instance.send_event(
            CLIMATE_EVENTGROUP_ID,
            CABIN_TEMPERATURE_CHANGED_EVENT_ID,
            payload,
        )

        print("CabinTemperatureChanged event sent")


async def main():

    set_someipy_log_level(logging.INFO)

    print("=" * 55)
    print("VIRTUAL CLIMATE ECU")
    print("SOME/IP ClimateService Provider")
    print("=" * 55)

    print(f"Service ID  : 0x{CLIMATE_SERVICE_ID:04X}")
    print(f"Instance ID : 0x{CLIMATE_INSTANCE_ID:04X}")
    print(
        f"Endpoint    : "
        f"{CLIMATE_INTERFACE_IP}:{CLIMATE_PROVIDER_PORT}"
    )

    print(
        "Cabin Temperature:",
        temp_to_text(current_cabin_temperature)
    )

    print(
        "Target Temperature:",
        temp_to_text(target_temperature)
    )

    print("=" * 55)

    print("Connecting to SOME/IP daemon...")

    daemon = await connect_to_someipy_daemon()

    print("Connected to SOME/IP daemon")

    provider_service = build_climate_provider()

    provider_instance = ServerServiceInstance(
        daemon=daemon,
        service=provider_service,
        instance_id=CLIMATE_INSTANCE_ID,
        endpoint_ip=CLIMATE_INTERFACE_IP,
        endpoint_port=CLIMATE_PROVIDER_PORT,
        ttl=5,
        cyclic_offer_delay_ms=2000,
    )

    print("Offering ClimateService...")

    await provider_instance.start_offer()

    print("ClimateService is being offered")

    temperature_task = asyncio.create_task(
        simulate_cabin_temperature(provider_instance)
    )

    try:
        await asyncio.Future()

    finally:
        temperature_task.cancel()

        try:
            await temperature_task
        except asyncio.CancelledError:
            pass

        await provider_instance.stop_offer()
        await daemon.disconnect_from_daemon()


if __name__ == "__main__":

    try:
        asyncio.run(main())

    except KeyboardInterrupt:
        print("\nClimate ECU stopped")
