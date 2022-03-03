from uModBusSerialServer import uModBusSerialServer
from uModBusServer import uModBusSequentialDataBank
import pyb

uart = pyb.UART(2, 9600)
modbus = uModBusSerialServer(uart, 9600, 0,
                             di=uModBusSequentialDataBank(0, [0]*10),
                             co=uModBusSequentialDataBank(100, [1, 0, 1, 0, 1, 0, 1, 0, 1, 0]),
                             hr=uModBusSequentialDataBank(200, [42]*100),
                             ir=uModBusSequentialDataBank(1000, [1]*10))

while True:
    try:
        modbus.update()
        pyb.delay(250)
    except KeyboardInterrupt:
        break
