"""Platform for sensor integration."""
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.components.binary_sensor import (
    BinarySensorEntity,
    BinarySensorDeviceClass
)

from .const import DOMAIN
from tion import Breezer, MagicAir

_LOGGER = logging.getLogger(__name__)

# Sensor types
POWER_BINARY_SENSOR = {
    "name": "power",
    "device_class": BinarySensorDeviceClass.POWER,
}


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities) -> bool:
    entities = []
    devices = hass.data[DOMAIN][entry.entry_id]["devices"]
    for guid in devices:
        device = devices[guid]
        if device.valid:
            if type(device) == Breezer:
                entities.append(TionBinarySensor(device, POWER_BINARY_SENSOR))
        else:
            _LOGGER.info(f"Skipped device {device}, because of 'valid' property")

    async_add_entities(entities, update_before_add=True)
    return True


class TionBinarySensor(BinarySensorEntity):
    """Representation of a Sensor."""

    def __init__(self, device: MagicAir | Breezer, sensor_type):
        self._device = device
        self._sensor_type = sensor_type
        if sensor_type.get('device_class', None) is not None:
            self._attr_device_class = sensor_type['device_class']

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self._device.guid)},
        }

    @property
    def unique_id(self):
        """Return a unique id identifying the entity."""
        return self._device.guid + self._sensor_type["name"]

    @property
    def name(self):
        """Return the name of the sensor."""
        return f"{self._device.name} {self._sensor_type['name']}"

    def update(self):
        """Fetch new state data for the sensor.
        This is the only method that should fetch new data for Home Assistant.
        """
        self._device.load()
        self._attr_is_on = self._device.speed > 0
