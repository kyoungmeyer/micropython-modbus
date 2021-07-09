# micropython-modbus
Modbus Master library for MicroPython STM32 devices. Based on pycom-modbus from pycom: https://github.com/pycom/pycom-modbus/

## Usage
Simply put `uModBusConst.py` and `uModBusFunctions.py`, as well as one or both of `uModBusSerial.py` and `uModBusTCP.py` in the same directory as your `main.py` file.

## Examples
### Serial
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
### Serial with RS485 Class
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
