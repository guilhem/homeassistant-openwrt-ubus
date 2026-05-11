"""Regression tests for OpenWrt ubus integration fixes.

These tests use small Home Assistant stubs so they can run without installing
Home Assistant locally. They are also pytest-compatible.
"""

from __future__ import annotations

import asyncio
import importlib
import sys
import types
import unittest
from pathlib import Path
from types import SimpleNamespace


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


class _DummySchema:
    def __init__(self, *args, **kwargs):
        pass

    def __call__(self, value):
        return value

    def extend(self, schema):
        return schema


class _Description:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


class _ConfigFlow:
    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__()

    def async_show_form(self, **kwargs):
        return {"type": "form", **kwargs}

    def async_create_entry(self, **kwargs):
        return {"type": "create_entry", **kwargs}


class _OptionsFlow:
    def __init__(self, *args, **kwargs):
        pass

    def async_show_form(self, **kwargs):
        return {"type": "form", **kwargs}

    def async_create_entry(self, **kwargs):
        return {"type": "create_entry", **kwargs}


class _DummyPlatformSchema:
    def extend(self, schema):
        return schema


class _DummyDeviceInfo(dict):
    def __init__(self, **kwargs):
        super().__init__(kwargs)


class _DummyClientSession:
    closed = False

    async def close(self):
        self.closed = True


class _ScannerEntity:
    pass


class _SensorEntity:
    pass


class _CoordinatorEntity:
    pass


def _enum(**values):
    return SimpleNamespace(**values)


def _install_stubs() -> None:
    """Install minimal dependency stubs required to import integration modules."""
    aiohttp = types.ModuleType("aiohttp")
    aiohttp.ClientConnectionError = ConnectionError
    aiohttp.ClientSession = _DummyClientSession
    sys.modules.setdefault("aiohttp", aiohttp)

    vol = types.ModuleType("voluptuous")
    vol.ALLOW_EXTRA = object()
    vol.Schema = _DummySchema
    vol.Required = lambda key, *args, **kwargs: key
    vol.Optional = lambda key, *args, **kwargs: key
    vol.In = lambda options: lambda value: value
    vol.All = lambda *validators: lambda value: value
    vol.Coerce = lambda converter: lambda value: converter(value)
    vol.Range = lambda *args, **kwargs: lambda value: value
    sys.modules.setdefault("voluptuous", vol)

    ha = types.ModuleType("homeassistant")
    sys.modules.setdefault("homeassistant", ha)

    const = types.ModuleType("homeassistant.const")
    const.CONF_HOST = "host"
    const.CONF_PASSWORD = "password"
    const.CONF_USERNAME = "username"
    const.CONF_IP_ADDRESS = "ip_address"
    const.CONF_VERIFY_SSL = "verify_ssl"
    const.PERCENTAGE = "%"
    const.SIGNAL_STRENGTH_DECIBELS = "dB"
    const.SIGNAL_STRENGTH_DECIBELS_MILLIWATT = "dBm"
    const.UnitOfTemperature = _enum(CELSIUS="C")
    const.UnitOfElectricPotential = _enum(MILLIVOLT="mV", VOLT="V")
    const.UnitOfTime = _enum(SECONDS="s")
    const.UnitOfInformation = _enum(BYTES="B")
    const.UnitOfDataRate = _enum(MEGABITS_PER_SECOND="Mbit/s")
    const.Platform = _enum(
        DEVICE_TRACKER="device_tracker",
        SENSOR="sensor",
        SWITCH="switch",
        BUTTON="button",
    )
    sys.modules.setdefault("homeassistant.const", const)

    config_entries = types.ModuleType("homeassistant.config_entries")
    config_entries.ConfigEntry = object
    config_entries.ConfigFlow = _ConfigFlow
    config_entries.ConfigFlowResult = dict
    config_entries.OptionsFlow = _OptionsFlow
    sys.modules.setdefault("homeassistant.config_entries", config_entries)

    core = types.ModuleType("homeassistant.core")
    core.HomeAssistant = object
    core.callback = lambda func: func
    sys.modules.setdefault("homeassistant.core", core)

    exceptions = types.ModuleType("homeassistant.exceptions")
    exceptions.ConfigEntryNotReady = RuntimeError
    exceptions.HomeAssistantError = RuntimeError
    sys.modules.setdefault("homeassistant.exceptions", exceptions)

    components = types.ModuleType("homeassistant.components")
    components.__path__ = []
    sys.modules.setdefault("homeassistant.components", components)

    device_tracker = types.ModuleType("homeassistant.components.device_tracker")
    device_tracker.PLATFORM_SCHEMA = _DummyPlatformSchema()
    device_tracker.ScannerEntity = _ScannerEntity
    device_tracker.SourceType = _enum(ROUTER="router")
    sys.modules.setdefault("homeassistant.components.device_tracker", device_tracker)

    sensor = types.ModuleType("homeassistant.components.sensor")
    sensor.SensorEntity = _SensorEntity
    sensor.SensorEntityDescription = _Description
    sensor.SensorDeviceClass = _enum(
        TEMPERATURE="temperature",
        VOLTAGE="voltage",
        SIGNAL_STRENGTH="signal_strength",
    )
    sensor.SensorStateClass = _enum(MEASUREMENT="measurement", TOTAL_INCREASING="total_increasing")
    sys.modules.setdefault("homeassistant.components.sensor", sensor)

    helpers = types.ModuleType("homeassistant.helpers")
    helpers.__path__ = []
    sys.modules.setdefault("homeassistant.helpers", helpers)

    cv = types.ModuleType("homeassistant.helpers.config_validation")
    cv.string = str
    cv.boolean = bool
    cv.multi_select = lambda options: lambda value: value
    sys.modules.setdefault("homeassistant.helpers.config_validation", cv)
    helpers.config_validation = cv

    device_registry = types.ModuleType("homeassistant.helpers.device_registry")
    device_registry.DeviceInfo = _DummyDeviceInfo
    device_registry.async_get = lambda hass: None
    sys.modules.setdefault("homeassistant.helpers.device_registry", device_registry)
    helpers.device_registry = device_registry

    entity_registry = types.ModuleType("homeassistant.helpers.entity_registry")
    entity_registry.async_get = lambda hass: None
    entity_registry.async_entries_for_config_entry = lambda registry, entry_id: []
    sys.modules.setdefault("homeassistant.helpers.entity_registry", entity_registry)
    helpers.entity_registry = entity_registry

    entity = types.ModuleType("homeassistant.helpers.entity")
    entity.EntityCategory = _enum(CONFIG="config", DIAGNOSTIC="diagnostic")
    sys.modules.setdefault("homeassistant.helpers.entity", entity)

    entity_platform = types.ModuleType("homeassistant.helpers.entity_platform")
    entity_platform.AddEntitiesCallback = object
    sys.modules.setdefault("homeassistant.helpers.entity_platform", entity_platform)

    aiohttp_client = types.ModuleType("homeassistant.helpers.aiohttp_client")
    aiohttp_client.async_get_clientsession = lambda *args, **kwargs: object()
    sys.modules.setdefault("homeassistant.helpers.aiohttp_client", aiohttp_client)

    typing_mod = types.ModuleType("homeassistant.helpers.typing")
    typing_mod.ConfigType = dict
    sys.modules.setdefault("homeassistant.helpers.typing", typing_mod)

    update_coordinator = types.ModuleType("homeassistant.helpers.update_coordinator")
    update_coordinator.CoordinatorEntity = _CoordinatorEntity
    update_coordinator.DataUpdateCoordinator = object
    update_coordinator.UpdateFailed = RuntimeError
    sys.modules.setdefault("homeassistant.helpers.update_coordinator", update_coordinator)

    sensors_pkg = types.ModuleType("custom_components.openwrt_ubus.sensors")
    sensors_pkg.__path__ = [str(ROOT / "custom_components" / "openwrt_ubus" / "sensors")]
    sys.modules.setdefault("custom_components.openwrt_ubus.sensors", sensors_pkg)


_install_stubs()


def _import_module(name: str):
    return importlib.import_module(name)


class _FakeDevice:
    def __init__(self, device_id: str, identifier: str, via_device_id: str | None = None):
        self.id = device_id
        self.identifiers = {("openwrt_ubus", identifier)}
        self.via_device_id = via_device_id


class _FakeDeviceRegistry:
    def __init__(self, devices: list[_FakeDevice]):
        self.devices = {device.id: device for device in devices}
        self.removed: list[str] = []

    def async_get_device(self, identifiers):
        for device in self.devices.values():
            if device.identifiers & identifiers:
                return device
        return None

    def async_remove_device(self, device_id: str):
        self.removed.append(device_id)
        self.devices.pop(device_id, None)


class RegressionTests(unittest.IsolatedAsyncioTestCase):
    async def test_ubus_reconnects_when_session_missing_or_near_expiry(self):
        interface = _import_module("custom_components.openwrt_ubus.Ubus.interface")
        ubus = interface.Ubus("http://router/ubus", "router", "user", "pass", object(), 15, False)

        connect_calls = 0

        async def fake_connect():
            nonlocal connect_calls
            connect_calls += 1
            ubus.session_id = "new-session"
            ubus.session_expire = interface.time.time() + 300
            return ubus.session_id

        ubus.connect = fake_connect
        ubus.session_id = None
        ubus.session_expire = interface.time.time() + 300
        await ubus._ensure_session_is_valid()
        self.assertEqual(connect_calls, 1)

        ubus.session_id = "valid-session"
        ubus.session_expire = interface.time.time() + 300
        await ubus._ensure_session_is_valid()
        self.assertEqual(connect_calls, 1)

        ubus.session_expire = interface.time.time() + 10
        await ubus._ensure_session_is_valid()
        self.assertEqual(connect_calls, 2)

    async def test_sta_selection_routes_to_wireless_tracker_config(self):
        config_flow = _import_module("custom_components.openwrt_ubus.config_flow")
        flow = config_flow.OpenwrtUbusConfigFlow()
        flow._sensor_data = {config_flow.CONF_ENABLE_WIRELESS_TRACKERS: True}

        async def wireless_step(user_input=None):
            return "wireless"

        async def wired_step(user_input=None):
            return "wired"

        flow.async_step_wireless_tracker_config = wireless_step
        flow.async_step_wired_tracker_config = wired_step

        result = await flow.async_step_sta_sensors_config({config_flow.CONF_SELECTED_STA: []})
        self.assertEqual(result, "wireless")

    async def test_cleanup_disabled_ap_does_not_remove_eth_device(self):
        integration = _import_module("custom_components.openwrt_ubus")
        registry = _FakeDeviceRegistry(
            [
                _FakeDevice("router", "router"),
                _FakeDevice("ap", "router_ap"),
                _FakeDevice("eth", "router_eth"),
                _FakeDevice("mwan3", "router_mwan3"),
            ]
        )
        entry = SimpleNamespace(
            data={
                integration.CONF_HOST: "router",
                integration.CONF_ENABLE_SYSTEM_SENSORS: True,
                integration.CONF_ENABLE_AP_SENSORS: False,
                integration.CONF_ENABLE_ETH_SENSORS: True,
                integration.CONF_ENABLE_MWAN3_SENSORS: True,
            },
            options={},
        )

        old_async_get = integration.dr.async_get
        integration.dr.async_get = lambda hass: registry
        try:
            await integration._cleanup_disabled_sensor_devices(SimpleNamespace(), entry)
        finally:
            integration.dr.async_get = old_async_get

        self.assertIn("ap", registry.removed)
        self.assertNotIn("eth", registry.removed)
        self.assertIn("eth", registry.devices)

    async def test_scan_devices_refreshes_matching_unique_coordinators(self):
        integration = _import_module("custom_components.openwrt_ubus")

        class Coordinator:
            def __init__(self, entry_id):
                self.data_manager = SimpleNamespace(entry=SimpleNamespace(entry_id=entry_id))
                self.refreshes = 0

            async def async_request_refresh(self):
                self.refreshes += 1

        first = Coordinator("entry-1")
        second = Coordinator("entry-2")
        hass = SimpleNamespace(
            data={
                integration.DOMAIN: {
                    "coordinators": [first, second],
                    "tracker_coordinators": {"entry-1": first},
                }
            }
        )

        refreshed = await integration._async_refresh_coordinators(hass, "entry-1")
        self.assertEqual(refreshed, 1)
        self.assertEqual(first.refreshes, 1)
        self.assertEqual(second.refreshes, 0)

    async def test_qmodem_availability_is_scoped_to_entry(self):
        qmodem_sensor = _import_module("custom_components.openwrt_ubus.sensors.qmodem_sensor")
        entry = SimpleNamespace(entry_id="entry-1")
        hass = SimpleNamespace(
            data={
                qmodem_sensor.DOMAIN: {
                    "availability": {"entry-1": {"modem_ctrl": False}},
                    "modem_ctrl_available": True,
                }
            }
        )

        result = await qmodem_sensor.async_setup_entry(hass, entry, lambda *args: None)
        self.assertIsNone(result)

    def test_wireless_whitelist_matches_ip_address_and_mac(self):
        device_tracker = _import_module("custom_components.openwrt_ubus.device_tracker")

        self.assertTrue(
            device_tracker._device_matches_wireless_whitelist(
                "AA:BB:CC:00:11:22",
                {"ip_address": "192.168.1.24"},
                ["192.168.1."],
            )
        )
        self.assertTrue(
            device_tracker._device_matches_wireless_whitelist(
                "AA:BB:CC:00:11:22",
                {"ip": "10.0.0.5"},
                ["AA:BB"],
            )
        )
        self.assertFalse(
            device_tracker._device_matches_wireless_whitelist(
                "AA:BB:CC:00:11:22",
                {"ip_address": "192.168.1.24"},
                ["10.0.0."],
            )
        )


if __name__ == "__main__":
    unittest.main()
