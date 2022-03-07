import network
import pyb
from uModBusSocketServer import uModBusSocketServer
from uModBusServer import uModBusSequentialDataBank

def server(ssid, psk):
    nic = network.RS9116()
    nic.init()
    print("Connecting...")
    nic.connect(ssid, psk)
    print("Connected.")
    host = nic.ifconfig()[0]
    port = 502

    modbus = uModBusSocketServer(host, port, 0,
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
