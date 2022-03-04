import struct
import logging
import uModBusConst as Const
from uModBusServer import uModBusSequentialServer


_logger = logging.getLogger(__name__)
_logger.setLevel(logging.INFO)

class uModBusSerialServer(uModBusSequentialServer):
    def __init__(self, uart, baudrate, server_id, **kwargs):
        self.uart = uart
        self.baudrate = baudrate
        super().__init__(server_id, **kwargs)

    def _send_data(self, data):
        response = data + self._calculate_crc16(data)
        self.uart.write(response)

    def _send_error_response(self, fx, exception):
        response = struct.pack('>BBB', self.server_id, Const.ERROR_BIAS + fx, exception)
        self._send_data(response)

    def update(self):
        if self.uart.any():
            # buffer = b'\x00\x03\x00\x00\x00\x01\x85\xdb'  # Read one holding reg from ID 0
            # TODO: Needs to split messages, maybe?
            buffer = self.uart.read()
            _logger.debug("Raw Input: {}".format(buffer))
            if len(buffer) > 7:
                server_id, fx = struct.unpack('>BB', buffer[:2])
                if server_id != self.server_id:
                    return None
                crc = buffer[-2:]
                if crc != self._calculate_crc16(buffer[:-2]):
                    # According to the MODBUS Application Protocol V1.1b, section 7:
                    # In the event of a CRC error, nothing is returned, and the client is allowed to time out.
                    _logger.error("CRC Error: {} != {}".format(crc, self._calculate_crc16(buffer[:-2])))
                    return None
                return self.handleRequest(fx, buffer)
        return None
