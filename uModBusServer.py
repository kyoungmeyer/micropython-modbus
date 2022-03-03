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


