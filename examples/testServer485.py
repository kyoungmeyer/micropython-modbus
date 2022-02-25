from uModBusServer import uModBusSerialServer
from uModBusServer import uModBusSequentialDataBank
import pyb
from rs485 import RS485

# This RS485 class is exclusive to the EMAC, Inc. CutiPy and Custom EMAC, Inc. boards
uart = RS485('E2', 'F11', 'D12', False, 3, 9600)
modbus = uModBusSerialServer(uart, 9600, 0,
                             di=uModBusSequentialDataBank(0, [0]*10),
                             co=uModBusSequentialDataBank(100, [1, 0, 1, 0, 1, 0, 1, 0, 1, 0]),
                             hr=uModBusSequentialDataBank(200, [42]*100),
                             ir=uModBusSequentialDataBank(1000, [1]*10))

while True:
    modbus.update()
    pyb.delay(250)
