import struct
import logging
import socket
import uModBusConst as Const
from uModBusServer import uModBusSequentialServer


_logger = logging.getLogger(__name__)
_logger.setLevel(logging.DEBUG)

class uModBusSocketServer(uModBusSequentialServer):
    def __init__(self, host, port, server_id, **kwargs):
        self.host = host
        self.port = port
        self.current_packet_id = 0
        super().__init__(server_id, **kwargs)
        self.server_socket = None
        self.connection_socket = None
        self._init_socket()

    def _send_data(self, fx, data):
        tcp_header = struct.pack('>HHHBB', self.current_packet_id, 0, len(data)+2, self.server_id, fx)
        _logger.debug("Send Header: {}".format(tcp_header))
        _logger.debug("Send Payload: {}".format(data))
        self.connection_socket.send(tcp_header+data)

    def _send_error_response(self, fx, exception):
        response = struct.pack('>B', exception)
        _logger.debug("Error Response: {}".format(response))
        self._send_data(Const.ERROR_BIAS + fx, response)

    def _init_socket(self):
        try:
            self.server_socket.close()
        except AttributeError:
            _logger.debug("Socket not open yet")
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(1)

    def update(self):
        _logger.debug("Listening on: {}:{}".format(self.host, self.port))
        self.connection_socket, address = self.server_socket.accept()
        _logger.debug("Received connection from {}".format(address))
        while True:
            try:
                _logger.debug("Waiting for message")
                buffer = self.connection_socket.recv(260)
            except OSError:
                break
            if buffer == b'':
                break
            _logger.debug("Raw Input: {}".format(buffer))
            if len(buffer) > 11:
                self.current_packet_id, _protocol, length, server_id, fx = struct.unpack('>HHHBB', buffer[:8])
                if server_id != self.server_id:
                    return None
                payload = buffer[8:8+length-2]
                self.handleRequest(fx, payload)
        return None


