"""
ClimateService interface for SOME/IP Assignment 2.
"""

from dataclasses import dataclass

from someipy import (
    Event,
    EventGroup,
    Method,
    ServiceBuilder,
    TransportLayerProtocol,
)

from someipy.serialization import SomeIpPayload, Sint16, Uint8


# Service identification
CLIMATE_SERVICE_ID = 0x2234
CLIMATE_INSTANCE_ID = 0x0001
CLIMATE_MAJOR_VERSION = 1

# Methods
GET_CABIN_TEMPERATURE_METHOD_ID = 0x0001
SET_TARGET_TEMPERATURE_METHOD_ID = 0x0002

# Event
CABIN_TEMPERATURE_CHANGED_EVENT_ID = 0x8001
CLIMATE_EVENTGROUP_ID = 0x0001

# Temperature limits (tenths of a degree Celsius)
MIN_TARGET_TEMPERATURE = 160
MAX_TARGET_TEMPERATURE = 300

# Response status
STATUS_ACCEPTED = 0
STATUS_INVALID_TEMPERATURE = 1

# Network configuration
CLIMATE_INTERFACE_IP = "127.0.0.1"
CLIMATE_PROVIDER_PORT = 3001
DISPLAY_CLIMATE_PORT = 3004


# Payload definitions
@dataclass
class CabinTemperaturePayload(SomeIpPayload):
    temperature: Sint16

    def __init__(self, temperature: int = 0):
        self.temperature = Sint16(temperature)


@dataclass
class TargetTemperaturePayload(SomeIpPayload):
    temperature: Sint16

    def __init__(self, temperature: int = 0):
        self.temperature = Sint16(temperature)


@dataclass
class SetTargetStatusPayload(SomeIpPayload):
    status: Uint8

    def __init__(self, status: int = 0):
        self.status = Uint8(status)


def temp_to_text(tenths: int) -> str:
    return f"{tenths / 10:.1f} degree Celsius"


def status_to_text(status: int) -> str:
    if status == STATUS_ACCEPTED:
        return "ACCEPTED"
    return "INVALID_TEMPERATURE"


# Method definitions
get_cabin_temperature_method = Method(
    id=GET_CABIN_TEMPERATURE_METHOD_ID,
    protocol=TransportLayerProtocol.UDP,
)

set_target_temperature_method = Method(
    id=SET_TARGET_TEMPERATURE_METHOD_ID,
    protocol=TransportLayerProtocol.UDP,
)


# Event definition
cabin_temperature_changed_event = Event(
    id=CABIN_TEMPERATURE_CHANGED_EVENT_ID,
    protocol=TransportLayerProtocol.UDP,
)

climate_eventgroup = EventGroup(
    id=CLIMATE_EVENTGROUP_ID,
    events=[cabin_temperature_changed_event],
)


# Build ClimateService
climate_service = (
    ServiceBuilder()
    .with_service_id(CLIMATE_SERVICE_ID)
    .with_major_version(CLIMATE_MAJOR_VERSION)
    .with_method(get_cabin_temperature_method)
    .with_method(set_target_temperature_method)
    .with_eventgroup(climate_eventgroup)
    .build()
)
