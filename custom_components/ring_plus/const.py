"""Constants for Ring Plus."""
from aioring.devices import ALL_CATEGORIES

DOMAIN = "ring_plus"
CONF_TOKEN = "token"
CONF_HARDWARE_ID = "hardware_id"
CONF_DEVICE_TYPES = "device_types"
DEFAULT_DEVICE_TYPES = list(ALL_CATEGORIES)
CAMERA_POLL_INTERVAL = 15
PLATFORMS = ["alarm_control_panel", "binary_sensor", "sensor", "camera"]
