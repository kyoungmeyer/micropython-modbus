# micropython-modbus
Modbus Client and Server library for MicroPython STM32 devices. Based on pycom-modbus from pycom: https://github.com/pycom/pycom-modbus/

## Usage
For client usage, simply put `uModBusConst.py` and `uModBusFunctions.py`, as well as one or both of `uModBusSerial.py` and `uModBusTCP.py` in the same directory as your `main.py` file. 

For server usage, put `uModBusConst.py` and `uModBusServer.py` as well as one or both of `uModBusSerialServer.py` and `uModBusSocketServer.py` (once complete) in the same directory as the `main.py` file.

## Examples
### Serial Client
For this STM32 port, a `UART` (`machine` or `pyb`) object is passed in as the first argument. This helps facilitate the use of classes that build on the UART class, such as an RS485 class.
```python
from uModBusSerial import uModBusSerial
from machine import UART

uart = UART(2, 9600)
modbus = uModbusSerial(uart, baudrate=9600)

regs = modbus.read_holding_registers(0, 0, 10)
print(regs)
```
```
(17, 17, 17, 17, 17, 17, 17, 17, 17, 17)
```
### Serial Client with RS485 Class
```python
from uModBusSerial import uModBusSerial
from rs485 import RS485

uart = RS485('E2', 'F11', 3, 9600)
modbus = uModbusSerial(uart, baudrate=9600)

regs = modbus.read_holding_registers(0, 0, 10)
print(regs)
```
```
(17, 17, 17, 17, 17, 17, 17, 17, 17, 17)
```
### Serial Server
```python
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
```
