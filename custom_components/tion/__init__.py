import logging
from threading import Timer

from homeassistant.const import CONF_USERNAME, CONF_PASSWORD, CONF_SCAN_INTERVAL, CONF_FILE_PATH, Platform
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from tion import TionApi, Breezer, MagicAir, ZonePreset
from tion.tion import TionZonesPresets, TionZones

from .const import DOMAIN

PLATFORMS: list[Platform] = [Platform.BINARY_SENSOR, Platform.SENSOR, Platform.CLIMATE, Platform.NUMBER, Platform.SWITCH]

MAGICAIR_DEVICE = "magicair"
BREEZER_DEVICE = "breezer"

_LOGGER = logging.getLogger(__name__)


async def async_setup(hass, config):
    return True


def create_api(user, password, interval, auth_fname):
    return TionApi(user, password, min_update_interval_sec=interval, auth_fname=auth_fname)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    # Setup DOMAIN as default
    hass.data.setdefault(DOMAIN, {})

    user_input = entry.data['user_input']

    api = await hass.async_add_executor_job(create_api,
                                            user_input[CONF_USERNAME],
                                            user_input[CONF_PASSWORD],
                                            user_input[CONF_SCAN_INTERVAL],
                                            user_input[CONF_FILE_PATH]
                                            )

    assert api.authorization, "Couldn't get authorisation data!"
    _LOGGER.info(f"Api initialized with authorization {api.authorization}")

    hass.data[DOMAIN][entry.entry_id] = {
        "api": api,
        "devices": {},
        "presets": {},
    }

    # Get the device registry
    device_registry = dr.async_get(hass)

    devices = await hass.async_add_executor_job(api.get_devices)
    models = {
        "co2mb": "MagicAir",
        "co2Plus": "Модуль CO2+",
        "tionO2Rf": "Бризер O2",
        "tionClever": "Clever",
        "breezer3": "Бризер 3S",
        "breezer4": "Бризер 4S"
    }
    device: Breezer
    for device in devices:
        if device.valid:
            device_type = BREEZER_DEVICE if type(device) == Breezer else (
                MAGICAIR_DEVICE if type(device) == MagicAir else None)
            if device_type:
                hass.data[DOMAIN][entry.entry_id]["devices"][device.guid] = device
                device_registry.async_get_or_create(
                    config_entry_id=entry.entry_id,
                    connections={(dr.CONNECTION_NETWORK_MAC, device.mac)},
                    identifiers={(DOMAIN, device.guid)},
                    manufacturer="TION",
                    model=models.get(device.type, "Unknown device"),
                    hw_version=device.hardware,
                    sw_version=device.firmware,
                    suggested_area=device.room,
                    name=device.name,
                )
            else:
                _LOGGER.info(f"Unused device {device}")
        else:
            _LOGGER.info(f"Skipped device {device}, because of 'valid' property")

    zone_presets = await hass.async_add_executor_job(api.get_zone_presets)
    zone_preset: ZonePreset
    for zone_preset in zone_presets:
        if zone_preset.valid:
            hass.data[DOMAIN][entry.entry_id]["presets"][zone_preset.guid] = ZonePresetWrapper(zone_preset)
            device_registry.async_get_or_create(
                config_entry_id=entry.entry_id,
                identifiers={(DOMAIN, zone_preset.guid)},
                manufacturer="TION",
                model="Расписание",
                suggested_area=zone_preset.room,
                name=f"{zone_preset.room} {zone_preset.name}",
            )

    # Forward to sensor platform
    await hass.async_create_task(hass.config_entries.async_forward_entry_setups(entry, PLATFORMS))

    return True


class ZonePresetWrapper(ZonePreset):
    _delay_save: bool = False
    _delay_load: bool = False
    _t: Timer = None

    def __init__(self, zone_preset: ZonePreset):
        self._api = zone_preset._api
        self._zone = zone_preset._zone
        self._guid = zone_preset._guid
        super().load()

    def load(self, preset_data: TionZonesPresets = None, zone_data: TionZones = None, force=False):
        if self._delay_save:
            self._delay_load = True
            return self.valid

        res = super().load(preset_data, zone_data, force)

        self._delay_load = False

        return res

    def send_internal(self) -> bool:
        res = super().send()
        self._delay_save = False
        if self._delay_load:
            self.load(None, None, True)
        return res

    def send(self) -> bool:
        self._delay_save = True

        if self._t is not None:
            try:
                self._t.cancel()
            except AttributeError:
                pass

        self._t = Timer(5, self.send_internal)
        self._t.start()

        return True
