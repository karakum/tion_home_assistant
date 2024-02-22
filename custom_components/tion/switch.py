"""Support for Tion breezer schedule preset"""
import logging
from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)

from . import DOMAIN, ZonePresetWrapper

MODE_AUTO_SWITCH = {
    "name": "mode_auto",
    "title": "автоуправление",
    "param": "mode",
}
BREEZER_ON_SWITCH = {
    "name": "breezer_on",
    "title": "включен",
    "param": "is_on",
}
HEATER_ON_SWITCH = {
    "name": "heater_on",
    "title": "нагреватель",
    "param": "heater_enabled",
}


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities) -> bool:
    entities = []
    zone_presets = hass.data[DOMAIN][entry.entry_id]["presets"]
    zone_preset: ZonePresetWrapper
    for guid in zone_presets:
        zone_preset = zone_presets[guid]
        if zone_preset.valid:
            entities.append(TionPresetSwitch(zone_preset, MODE_AUTO_SWITCH))
            entities.append(TionPresetSwitch(zone_preset, BREEZER_ON_SWITCH))
            entities.append(TionPresetSwitch(zone_preset, HEATER_ON_SWITCH))
        else:
            _LOGGER.info(f"Skipped preset {zone_preset}, because of 'valid' property")

    async_add_entities(entities, update_before_add=True)

    return True


class TionPresetSwitch(SwitchEntity):
    """Tion schedule preset"""

    _attr_has_entity_name = False

    def __init__(self, preset: ZonePresetWrapper, switch_type):
        """Init climate device."""
        self._preset: ZonePresetWrapper = preset
        self._switch_type = switch_type

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self._preset.guid)},
        }

    @property
    def unique_id(self):
        """Return a unique id identifying the entity."""
        return self._preset.guid + self._switch_type['name']

    @property
    def name(self):
        """Return the name of the sensor."""
        return f"{self._preset.room} {self._preset.name} {self._switch_type['title']}"

    @property
    def suggested_object_id(self):
        """Return the name of the sensor."""
        return f"tion_preset_{self._preset.room}_{self._preset.index}_{self._switch_type['name']}"

    def update(self):
        """Fetch new state data for the breezer.
        This is the only method that should fetch new data for Home Assistant.
        """
        self._preset.load()
        self._attr_is_on = None
        if self._switch_type == MODE_AUTO_SWITCH:
            self._attr_is_on = self._preset.mode == "auto"
        elif self._switch_type == BREEZER_ON_SWITCH:
            self._attr_is_on = self._preset.is_on
        elif self._switch_type == HEATER_ON_SWITCH:
            self._attr_is_on = self._preset.heater_enabled

    def turn_on(self, **kwargs: Any) -> None:
        self._attr_is_on = True
        if self._switch_type == MODE_AUTO_SWITCH:
            self._preset.mode = "auto"
        elif self._switch_type == BREEZER_ON_SWITCH:
            self._preset.is_on = True
        elif self._switch_type == HEATER_ON_SWITCH:
            self._preset.heater_enabled = True
        self._preset.send()

    def turn_off(self, **kwargs: Any) -> None:
        self._attr_is_on = False
        if self._switch_type == MODE_AUTO_SWITCH:
            self._preset.mode = "manual"
        elif self._switch_type == BREEZER_ON_SWITCH:
            self._preset.is_on = False
        elif self._switch_type == HEATER_ON_SWITCH:
            self._preset.heater_enabled = False
        self._preset.send()

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return self._preset.valid
