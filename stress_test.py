import threading
from device import Device

device_list = []

for _ in range(1000):
    device_list.append( Device() )
    # start device loop:
    device_list[-1].start_mqtt_client()
    device_list[-1].register_device() # shouldn't be done every time, we need a local file to save the info that device is registered
    threading.Thread( target=device_list[-1].device_loop ).start()
    

print("Started all devices")