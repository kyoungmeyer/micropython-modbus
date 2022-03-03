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

    def _send_error_response(self, fx, exception):
        response = struct.pack('>BBB', self.server_id, Const.ERROR_BIAS + fx, exception)
        response += self._calculate_crc16(response)
        self.uart.write(response)

    def handleRead(self, fx, buffer):
        if fx in (Const.READ_HOLDING_REGISTERS, Const.READ_INPUT_REGISTER):
            _logger.debug("Read {} Register".format(fx))
            address, count = struct.unpack('>HH', buffer[2:6])
            if self.validate(fx, address, count):
                response = struct.pack('>BBB', self.server_id, fx, count*2)
                rsp_values = self.getValues(fx, address, count)
                _logger.debug(rsp_values)
                response += struct.pack('>{}H'.format(count), *list(rsp_values))
                response += self._calculate_crc16(response)
                self.uart.write(response)
            else:
                self._send_error_response(fx, Const.ILLEGAL_DATA_ADDRESS)
        else:
            _logger.debug("Read {} Register".format(fx))
            address, count = struct.unpack('>HH', buffer[2:6])
            if self.validate(fx, address, count):
                response = struct.pack('>BBB', self.server_id, fx, (count + 7)//8)
                values = self.getValues(fx, address, count)
                payload = 0
                for digit in reversed(values):
                    payload = (payload << 1) | digit
                payload = payload.to_bytes((count+7)//8, 'little')
                # payload = int("".join(str(x) for x in values), 2).to_bytes((count+7)//8, 'big')
                response += payload
                response += self._calculate_crc16(response)
                self.uart.write(response)
            else:
                self._send_error_response(fx, Const.ILLEGAL_DATA_ADDRESS)

    def handleWriteSingle(self, fx, buffer):
        _logger.debug("Write Single Coil or Register")
        address, value = struct.unpack('>HH', buffer[2:6])
        if self.validate(fx, address, 1):
            if fx == Const.WRITE_SINGLE_COIL:
                if value in [0x00, 0xFF00]:
                    self.setValues(fx, address, ([False] if value == 0x0000 else [True]))
                else:
                    self._send_error_response(fx, Const.ILLEGAL_DATA_VALUE)
            else:
                self.setValues(fx, address, [value])
            self.uart.write(buffer)
        else:
            self._send_error_response(fx, Const.ILLEGAL_DATA_ADDRESS)

    def handleWriteMultiple(self, fx, buffer):
        if fx == Const.WRITE_MULTIPLE_COILS:
            address, outputs, count = struct.unpack('>HHB', buffer[2:7])
            _logger.debug("Write Multiple ({}) Coils".format(outputs))
            values = struct.unpack('>{}B'.format(count), buffer[7:])
            _logger.debug("Values to set {}".format(values))
            if self.validate(fx, address, outputs):
                val_list = self._bits_to_bool_list(values, outputs)
                _logger.debug("Bool values to set {}".format(val_list))
                if val_list is not None:
                    self.setValues(fx, address, val_list)
                    response = struct.pack('>BBHH', self.server_id, fx, address, outputs)
                    response += self._calculate_crc16(response)
                    self.uart.write(response)
                else:
                    self._send_error_response(fx, Const.ILLEGAL_DATA_VALUE)
            else:
                self._send_error_response(fx, Const.ILLEGAL_DATA_ADDRESS)
        else:  # Const.WRITE_MULTIPLE_REGISTERS
            address, num_regs, _count = struct.unpack('>HHB', buffer[2:7])
            _logger.debug("Write Multiple ({}) Registers".format(num_regs))
            values = struct.unpack('>{}H'.format(num_regs), buffer[7:])
            if self.validate(fx, address, num_regs):
                self.setValues(fx, address, list(values))
                response = struct.pack('>BBHH', self.server_id, fx, address, num_regs)
                response += self._calculate_crc16(response)
                self.uart.write(response)
            else:
                self._send_error_response(fx, Const.ILLEGAL_DATA_ADDRESS)

    def handleWrite(self, fx, buffer):
        if fx in (Const.WRITE_SINGLE_COIL, Const.WRITE_SINGLE_REGISTER):
            self.handleWriteSingle(fx, buffer)
        else:
            self.handleWriteMultiple(fx, buffer)

    def handleRequest(self, fx, buffer):
        if fx in (Const.READ_COILS, Const.READ_DISCRETE_INPUTS, Const.READ_HOLDING_REGISTERS, Const.READ_INPUT_REGISTER):
            self.handleRead(fx, buffer)
        elif fx in (Const.WRITE_SINGLE_COIL, Const.WRITE_SINGLE_REGISTER, Const.WRITE_MULTIPLE_COILS, Const.WRITE_MULTIPLE_REGISTERS):
            self.handleWrite(fx, buffer)
        else:
            # Error Not Supported
            self._send_error_response(fx, Const.ILLEGAL_FUNCTION)

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
