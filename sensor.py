"""Sensor for Zortrax Plus printer."""
from datetime import timedelta
import logging

import voluptuous as vol

from homeassistant.components.sensor import PLATFORM_SCHEMA
from homeassistant.const import VOLUME_LITERS
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity import Entity

_LOGGER = logging.getLogger(__name__)

SCAN_INTERVAL = timedelta(seconds=10)

CONF_ICON = "mdi:printer"
DEFAULT_NAME = "Zortrax Plus Printer"
CONF_ZPRINTER_HOST = "zprinter_host"
CONF_ZPRINTER_PORT = "zprinter_port"

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_ZPRINTER_HOST): cv.string,
        vol.Optional(CONF_ZPRINTER_PORT, default=8002): cv.port,
        vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
    }
)


def setup_platform(hass, config, add_entities, discovery_info=None):
    """Set up a Zortrax Plus Printer Camera."""
    if discovery_info:
        config = PLATFORM_SCHEMA(discovery_info)
    add_entities([ZortraxPrinter(config)])


class ZortraxPrinter(Entity):
    """Representation of a Sensor."""

    def __init__(self, device_info):
        """Initialize Zortrax Plus Printer Camera."""
        super().__init__()
        self._name = device_info.get(CONF_NAME)
        self._zprinter_host = device_info.get(CONF_ZPRINTER_HOST)
        self._zprinter_port = device_info.get(CONF_ZPRINTER_PORT)
        self._attributes = {}
        self._available = None
        self._state = None
        self.client = device_info

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._state

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement."""
        return VOLUME_LITERS

    @property
    def device_state_attributes(self):
        """Return the state attributes."""
        return self._attributes

    @property
    def icon(self):
        """Return the icon of the sensor."""
        return COMPONENT_ICON

    def get_json_packet(self, json_request):
        """Return json reply from the Zortrax Plus Printer."""
        json_request_len = len(json_request)
        json_request_packed = struct.pack(">h", json_request_len) + json_request.encode('ascii')
        _LOGGER.debug("Trying to connect to the printer at %s:%s to send '%s'" % (self._zprinter_host, self._zprinter_port, str(json_request_packed)))

        stcp = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        stcp.settimeout(10)

        try:
            stcp.connect((self._zprinter_host, int(self._zprinter_port)))
        except:
            _LOGGER.debug("Printer currently unavailable at %s:%s" % (self._zprinter_host, self._zprinter_port))
            self._available = False
            return

        _LOGGER.debug("Printer connected at %s:%s" % (self._zprinter_host, self._zprinter_port))
        self._available = True
        stcp.sendall(json_request_packed)
        data = ''
        while True:
            datachunk = stcp.recv(4096)
            if not datachunk:
                break
            data += datachunk.decode('ascii')
        stcp.close()

        _LOGGER.debug('Received data from the printer with length %d bytes' % (len(data)))

        json_reply = json.loads(data)

        return json_reply


    def get_status(self):
        """Get a Zortrax Plus Printer Camera frame"""
        status = {}
        to_printer = {}
        commands = []
        command = {}
        command['type'] = 'status'
        command['fields'] = ["printerStatus","storageBytesFree","storageBytesTotal","currentMaterialId","failsafeReason","serialNumber","printingInProgress","failsafeAlertReason","failsafeAlertSource"]
        commands.append(command)
        to_printer['commands'] = commands

        json_request = json.dumps(to_printer)
        json_response = self.camera_get_json_packet(json_request)

        if not self._available:
            return

        if 'responses' in json_response and 'fields' in json_response['responses'][0] and json_response['responses'][0]['status'] == "1":
            for field in json_response['responses'][0]['fields']:
                status[field['name']] = status['value']

        return status


    def _fetch_data(self):
        """Fetch latest Zortrax Plus data."""
        try:
            self.client.update()
            self._state = self.client.state
            self._available = True
            for k,v in get_status():
                self._attributes[k] = vol
        except:
            _LOGGER.error("Unable to fetch data")

    def update(self):
        """Return the latest collected data from the printer."""
        self._fetch_data()
        _LOGGER.debug("Zortrax Plus Printer data state is: %s.", self._state)

