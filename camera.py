"""Support for Zortrax Plus Printer Cameras."""
import logging
import base64
import socket
import json
import struct
from io import BytesIO
from PIL import Image

import voluptuous as vol

from homeassistant.const import (
    CONF_NAME,
)
from homeassistant.components.camera import PLATFORM_SCHEMA, Camera

from homeassistant.helpers import config_validation as cv

_LOGGER = logging.getLogger(__name__)

CONF_ZCAMERA_HOST = "zcamera_host"
CONF_ZCAMERA_PORT = "zcamera_port"
CONF_ZCAMERA_QUALITY = "zcamera_quality"
CONTENT_TYPE_HEADER = "Content-Type"

DEFAULT_NAME = "Zortrax Plus Camera"

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_ZCAMERA_HOST): cv.string,
        vol.Optional(CONF_ZCAMERA_PORT, default=8002): cv.port,
        vol.Optional(CONF_ZCAMERA_QUALITY, default=80): vol.Coerce(int),
        vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
    }
)

async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Set up a Zortrax Plus Printer Camera."""
    if discovery_info:
        config = PLATFORM_SCHEMA(discovery_info)
    async_add_entities([ZortraxCamera(config)])


class ZortraxCamera(Camera):

    def __init__(self, device_info):
        """Initialize Zortrax Plus Printer Camera."""
        super().__init__()
        self._name = device_info.get(CONF_NAME)
        self._zcamera_host = device_info.get(CONF_ZCAMERA_HOST)
        self._zcamera_port = device_info.get(CONF_ZCAMERA_PORT)
        self._zcamera_quality = device_info.get(CONF_ZCAMERA_QUALITY)
        self._available = False

    def available(self) -> bool:
        """Return True if entity is available."""
        return self._available

    async def async_camera_image(self):
        """Return a still image response from the Zortrax Plus Printer Camera."""
        image = await self.hass.async_add_job(self.camera_image)
        
        if not self._available:
            return

        return image


    def camera_get_json_packet(self, json_request):
        """Return json reply from the Zortrax Plus Printer."""
        json_request_len = len(json_request)
        json_request_packed = struct.pack(">h", json_request_len) + json_request.encode('ascii')
        _LOGGER.debug("Trying to connect to the printer at %s:%s to send '%s'" % (self._zcamera_host, self._zcamera_port, str(json_request_packed)))

        stcp = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        stcp.settimeout(10)

        try:
            stcp.connect((self._zcamera_host, int(self._zcamera_port)))
        except:
            _LOGGER.debug("Printer currently unavailable at %s:%s" % (self._zcamera_host, self._zcamera_port))
            self._available = False
            return

        _LOGGER.debug("Printer connected at %s:%s" % (self._zcamera_host, self._zcamera_port))
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


    def camera_image(self):
        """Get a Zortrax Plus Printer Camera frame"""
        to_printer = {}
        commands = []
        command = {}
        command['type'] = 'getCameraPreview'
        command['quality'] = int(self._zcamera_quality)
        commands.append(command)
        to_printer['commands'] = commands

        json_request = json.dumps(to_printer)
        json_response = self.camera_get_json_packet(json_request)

        if not self._available:
            return

        if 'responses' in json_response and json_response['responses'][0]['type'] == "getCameraPreview" and json_response['responses'][0]['status'] == "1":
            json_response_b64 = json_response['responses'][0]['cameraPreviewData']
            imgdata = base64.b64decode(json_response_b64)
            _LOGGER.debug("Found image in the data received by the printer")
        else:
            _LOGGER.error("Got data from the printer without image. Protocol may be changed.")

        with BytesIO() as imgbufin:
            imgbufin.write(imgdata)
            imgbufin.seek(0)
            im = Image.open(imgbufin)
            im = im.rotate(180)

        with BytesIO() as imgbufout:
            im.save(imgbufout, format="JPEG")
            imgout = imgbufout.getvalue()
        
        return imgout


    @property
    def name(self):
        """Return the name of this camera."""
        return self._name
