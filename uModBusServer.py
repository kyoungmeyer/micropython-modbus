import uModBusConst as Const
from collections import namedtuple
import struct

Databank = namedtuple("Databank", "coil discrete holding input")


class RegisterExists(Exception):
    """Raised when a register already exists"""
    pass


class uModBusSerialServer:
    COIL = 0x01
    DISCRETE_INPUT = 0x02
    HOLDING = 0x03
    INPUT = 0x04

    def __init__(self, uart, baudrate, server_id):
        self.uart = uart
        self.baudrate = baudrate
        self.server_id = server_id
        self.databank = Databank({}, {}, {}, {})

    def _calculate_crc16(self, data):
        crc = 0xFFFF

        for char in data:
            crc = (crc >> 8) ^ Const.CRC16_TABLE[((crc) ^ char) & 0xFF]

        return struct.pack('<H', crc)

    def _read_holding_registers(self, address, length):
        # Grabs a series of values from the databank, and
        # packs them 'big endian' into a bytearray
        return struct.pack('>' + 'H' * length, *[self.databank.holding[x] for x in range(address, address+length)])

    def add(self, address, reg_type, value=None):
        for buffer in self.databank:
            if address in buffer.keys():
                raise RegisterExists
        self.databank[reg_type-1][address] = value

    def update(self):
        if self.uart.any():
            # buffer = b'\x00\x03\x00\x00\x00\x01\x85\xdb'  # Read one holding reg from ID 0
            # TODO: Needs to split messages, maybe?
            buffer = self.uart.read()
            if len(buffer) > 7:
                server_id, function, start_addr, number_regs = struct.unpack('>BBHH', buffer[:6])
                crc = buffer[-2:]
                if (crc != self._calculate_crc16(buffer[:-2])):
                    # TODO: Do something for the error case
                    print("CRC Error: {} != {}".format(crc, self._calculate_crc16(buffer[:-2])))

                if function == Const.READ_HOLDING_REGISTERS:
                    if all(x in self.databank.holding for x in range(start_addr, start_addr+number_regs)):
                        response = struct.pack('>BBB', self.server_id, function, number_regs*2)
                        response += self._read_holding_registers(start_addr, number_regs)
                        response += self._calculate_crc16(response)
                        self.uart.write(response)
        else:
            return None
