"""Support for Zortrax Plus Printer."""
import logging
import base64
import socket
import json
import struct

import voluptuous as vol

from homeassistant.components.switch import SwitchDevice, PLATFORM_SCHEMA
from homeassistant.const import CONF_ZPRINTER_HOST, CONF_ZPRINTER_PORT, CONF_NAME
import homeassistant.helpers.config_validation as cv

_LOGGER = logging.getLogger(__name__)

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
    _LOGGER.debug("ADD ENTITY")
    """Set up a Zortrax Plus Printer."""
    if discovery_info:
        config = PLATFORM_SCHEMA(discovery_info)
    add_entities([ZortraxPrinter(config)])


class ZortraxPrinter(SwitchDevice):

    def __init__(self, smartplug, name):
        """Initialize the switch."""
        _LOGGER.debug("Init switch")
        self._name = device_info.get(CONF_NAME)
        self._zprinter_host = device_info.get(CONF_ZPRINTER_HOST)
        self._zprinter_port = device_info.get(CONF_ZPRINTER_PORT)
        self._printing = None
        self._state = None

    @property
    def name(self):
        _LOGGER.debug("Return name")
        """Return the name of the switch."""
        return self._name

    @property
    def state(self):
        _LOGGER.debug("Return state")
        """Return true if switch is on."""
        return self._state

    @property
    def icon(self):
        _LOGGER.debug("Return icon")
        """Return the icon of the sensor."""
        return CONF_ICON

    def get_json_packet(self, json_request):
        _LOGGER.debug("Return json pack")
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


    def turn_on(self, **kwargs):
        """Turn the switch on."""
        _LOGGER.info("DO NOTHING: ON")

    def turn_off(self, **kwargs):
        """Turn the switch off."""
        _LOGGER.info("DO NOTHING: OFF")

    def update(self):
        _LOGGER.debug("Return upd")
        """Update Zortrax Plus Printer state"""
        status = {}
        to_printer = {}
        commands = []
        command = {}
        command['type'] = 'status'
        command['fields'] = ["printerStatus","storageBytesFree","storageBytesTotal","currentMaterialId","failsafeReason","serialNumber","printingInProgress","failsafeAlertReason","failsafeAlertSource"]
        commands.append(command)
        to_printer['commands'] = commands

        json_request = json.dumps(to_printer)
        json_response = self.get_json_packet(json_request)

        if not self._available:
            return

        if 'responses' in json_response and 'fields' in json_response['responses'][0] and json_response['responses'][0]['status'] == "1":
            for field in json_response['responses'][0]['fields']:
                if field['name'] == 'printerStatus'
                    self._state = field['value']
                    _LOGGER.debug("Got Zortrax Printer state '%s'" % (self._state))
                    return
