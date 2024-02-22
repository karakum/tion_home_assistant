"""Support for Tion breezer schedule preset"""
import logging

from homeassistant.components.number import NumberEntity
from homeassistant.components.number.const import NumberMode, NumberDeviceClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTemperature
from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)

from . import DOMAIN, ZonePresetWrapper

CO2_NUMBER = {
    "name": "co2",
    "title": "целевой CO₂",
    "device_class": NumberDeviceClass.CO2,
    "mode": NumberMode.SLIDER,
    "native_min_value": 550,
    "native_max_value": 1500,
    "native_step": 50,
    "native_unit_of_measurement": "ppm",
}
SPEED_NUMBER = {
    "name": "speed",
    "title": "скорость",
    "mode": NumberMode.SLIDER,
    "native_min_value": 1,
    "native_max_value": 6,
    "native_step": 1,
}
SPEED_MIN_SET_NUMBER = {
    "name": "speed_min_set",
    "title": "скорость MIN",
    "mode": NumberMode.SLIDER,
    "native_min_value": 0,
    "native_max_value": 6,
    "native_step": 1,
}
SPEED_MAX_SET_NUMBER = {
    "name": "speed_max_set",
    "title": "скорость MAX",
    "mode": NumberMode.SLIDER,
    "native_min_value": 0,
    "native_max_value": 6,
    "native_step": 1,
}
T_SET_NUMBER = {
    "name": "t_set",
    "title": "температура",
    "device_class": NumberDeviceClass.TEMPERATURE,
    "mode": NumberMode.SLIDER,
    "native_min_value": 0,
    "native_max_value": 30,
    "native_step": 1,
    "native_unit_of_measurement": UnitOfTemperature.CELSIUS,
}


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities) -> bool:
    entities = []
    zone_presets = hass.data[DOMAIN][entry.entry_id]["presets"]
    zone_preset: ZonePresetWrapper
    for guid in zone_presets:
        zone_preset = zone_presets[guid]
        if zone_preset.valid:
            entities.append(TionPresetNumber(zone_preset, CO2_NUMBER))
            entities.append(TionPresetNumber(zone_preset, SPEED_NUMBER))
            entities.append(TionPresetNumber(zone_preset, SPEED_MIN_SET_NUMBER))
            entities.append(TionPresetNumber(zone_preset, SPEED_MAX_SET_NUMBER))
            entities.append(TionPresetNumber(zone_preset, T_SET_NUMBER))
        else:
            _LOGGER.info(f"Skipped preset {zone_preset}, because of 'valid' property")

    async_add_entities(entities, update_before_add=True)

    return True


class TionPresetNumber(NumberEntity):
    """Tion schedule preset"""

    _attr_has_entity_name = False

    def __init__(self, preset: ZonePresetWrapper, number_type):
        """Init climate device."""
        self._preset: ZonePresetWrapper = preset
        self._number_type = number_type
        if number_type.get("device_class", None) is not None:
            self._attr_device_class = number_type["device_class"]
        if number_type.get("mode", None) is not None:
            self._attr_mode = number_type["mode"]
        if number_type.get("native_min_value", None) is not None:
            self._attr_native_min_value = number_type["native_min_value"]
        if number_type.get("native_max_value", None) is not None:
            self._attr_native_max_value = number_type["native_max_value"]
        if number_type.get("native_step", None) is not None:
            self._attr_native_step = number_type["native_step"]
        if number_type.get("native_unit_of_measurement", None) is not None:
            self._attr_native_unit_of_measurement = number_type["native_unit_of_measurement"]

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self._preset.guid)},
        }

    @property
    def unique_id(self):
        """Return a unique id identifying the entity."""
        return self._preset.guid + self._number_type['name']

    @property
    def name(self):
        """Return the name of the sensor."""
        return f"{self._preset.room} {self._preset.name} {self._number_type['title']}"

    @property
    def suggested_object_id(self):
        """Return the name of the sensor."""
        return f"tion_preset_{self._preset.room}_{self._preset.index}_{self._number_type['name']}"

    def update(self):
        """Fetch new state data for the breezer.
        This is the only method that should fetch new data for Home Assistant.
        """
        self._preset.load()
        self._attr_native_value = None
        if self._number_type == CO2_NUMBER:
            self._attr_native_value = float(self._preset.co2)
        elif self._number_type == SPEED_NUMBER:
            self._attr_native_value = float(self._preset.speed)
        elif self._number_type == SPEED_MIN_SET_NUMBER:
            self._attr_native_value = float(self._preset.speed_min_set)
        elif self._number_type == SPEED_MAX_SET_NUMBER:
            self._attr_native_value = float(self._preset.speed_max_set)
        elif self._number_type == T_SET_NUMBER:
            self._attr_native_value = float(self._preset.t_set)

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return self._preset.valid

    def set_native_value(self, value: float) -> None:
        self._attr_native_value = value
        if self._number_type == CO2_NUMBER:
            self._preset.co2 = value
        elif self._number_type == SPEED_NUMBER:
            self._preset.speed = value
        elif self._number_type == SPEED_MIN_SET_NUMBER:
            self._preset.speed_min_set = value
        elif self._number_type == SPEED_MAX_SET_NUMBER:
            self._preset.speed_max_set = value
        elif self._number_type == T_SET_NUMBER:
            self._preset.t_set = value
        self._preset.send()
