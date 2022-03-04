import struct
import logging
import uModBusConst as Const

###
# The databank structure was heavily inspired by the pymodbus project
# https://github.com/riptideio/pymodbus
###

_logger = logging.getLogger(__name__)
_logger.setLevel(logging.INFO)


class ModbusException(Exception):
    """ Base modbus exception """

    def __init__(self, string):
        """ Initialize the exception
        :param string: The message to append to the error
        """
        self.string = string
        super().__init__(self.string)

    def __str__(self):
        return 'Modbus Error: %s' % self.string

    @classmethod
    def isError(cls):
        """Error"""
        return True


class NotImplementedException(ModbusException):
    """ Error resulting from not implemented function """

    def __init__(self, string=""):
        """ Initialize the exception
        :param string: The message to append to the error
        """
        message = "[Not Implemented] %s" % string
        ModbusException.__init__(self, message)


class uModBusDataBank:
    def __init__(self, address, values, default):
        self.default_value = default
        self.values = values
        self.address = address

    def default(self, count, value=False):
        self.default_value = value
        self.values = [self.default_value] * count
        self.address = 0x00

    def reset(self):
        self.values = [self.default_value] * len(self.values)

    def validate(self, address, count=1):
        raise NotImplementedException("Datastore Address Check: {}".format(self.address))

    def getValues(self, address, count=1):
        raise NotImplementedException("Datastore Value Retrieve {}".format(self.address))

    def setValues(self, address, values):
        raise NotImplementedException("Datastore Value Retrieve {}".format(self.address))

    def __str__(self):
        return "DataStore(%d, %d)" % (len(self.values), self.default_value)

    def __iter__(self):
        return enumerate(self.values, self.address)


class uModBusSequentialDataBank(uModBusDataBank):
    def __init__(self, address, values):
        self.address = address
        if isinstance(values, (list, dict, tuple)):
            self.values = list(values)
        else:
            self.values = [values]
        self.default_value = self.values[0].__class__()
        super().__init__(self.address, self.values, self.default_value)

    @classmethod
    def create(cls):
        return cls(0x00, [0x00] * 1024)

    def validate(self, address, count=1):
        result = (self.address <= address)
        result &= ((self.address + len(self.values)) >= (address + count))
        return result

    def getValues(self, address, count=1):
        start = address - self.address
        return self.values[start:start+count]

    def setValues(self, address, values):
        if not isinstance(values, list):
            values = [values]
        start = address - self.address
        self.values[start:start + len(values)] = values


class uModBusServer:
    __fx_mapper = {2: 'd', 4: 'i'}
    __fx_mapper.update([(i, 'h') for i in [3, 6, 16, 22, 23]])
    __fx_mapper.update([(i, 'c') for i in [1, 5, 15]])

    @classmethod
    def _calculate_crc16(cls, data):
        crc = 0xFFFF

        for char in data:
            crc = (crc >> 8) ^ Const.CRC16_TABLE[((crc) ^ char) & 0xFF]

        return struct.pack('<H', crc)

    def _decode(self, fx):
        return self.__fx_mapper[fx]

    @classmethod
    def _bytes_to_bool(cls, byte_list):
        bool_list = []
        for _, byte in enumerate(byte_list):
            bool_list.extend([bool(byte & (1 << n)) for n in range(8)])
        return bool_list

    @classmethod
    def _bits_to_bool_list(cls, data, num_bits):
        ret_list = []
        current_bit = 0
        for elem in data:
            for bit in range(8):
                ret_list.append(bool((elem >> bit) & 1))
                current_bit += 1
                if current_bit == num_bits:
                    return ret_list
        return None  # Should never reach, just to satisfy linter

    @classmethod
    def validate(cls, fx, address, count=1):
        raise NotImplementedException("validate context values")

    @classmethod
    def getValues(cls, fx, address, count=1):
        raise NotImplementedException("get context values")

    @classmethod
    def setValues(cls, fx, address, values):
        raise NotImplementedException("set context values")

    def _send_data(self, data):
        raise NotImplementedException("Send data")

    def _send_error_response(self, fx, exception):
        raise NotImplementedException("Send error response")


class uModBusSequentialServer(uModBusServer):
    def __init__(self, server_id, **kwargs):
        self.server_id = server_id
        self.databank = {}
        self.databank['d'] = kwargs.get('di', uModBusSequentialDataBank.create())
        self.databank['c'] = kwargs.get('co', uModBusSequentialDataBank.create())
        self.databank['i'] = kwargs.get('ir', uModBusSequentialDataBank.create())
        self.databank['h'] = kwargs.get('hr', uModBusSequentialDataBank.create())

    def validate(self, fx, address, count=1):
        _logger.debug("validate: fc-[%d] address-%d: count-%d" % (fx, address,
                                                                  count))
        return self.databank[self._decode(fx)].validate(address, count)

    def getValues(self, fx, address, count=1):
        _logger.debug("getValues fc-[%d] address-%d: count-%d" % (fx, address,
                                                                  count))
        return self.databank[self._decode(fx)].getValues(address, count)

    def setValues(self, fx, address, values):
        _logger.debug("setValues[%d] %d:%d" % (fx, address, len(values)))
        self.databank[self._decode(fx)].setValues(address, values)

    def handleRead(self, fx, buffer):
        if fx in (Const.READ_HOLDING_REGISTERS, Const.READ_INPUT_REGISTER):
            _logger.debug("Read {} Register".format(fx))
            address, count = struct.unpack('>HH', buffer[2:6])
            if self.validate(fx, address, count):
                response = struct.pack('>BBB', self.server_id, fx, count*2)
                rsp_values = self.getValues(fx, address, count)
                _logger.debug(rsp_values)
                response += struct.pack('>{}H'.format(count), *list(rsp_values))
                self._send_data(response)
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
                self._send_data(response)
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
            self._send_data(buffer)
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
                    self._send_data(response)
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
                self._send_data(response)
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
