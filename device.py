import sys
import time
import json
import numpy
import random
import datetime
import paho.mqtt.client as mqtt

import settings

def get_random_id():
    return "-".join(['{:x}'.format(random.randint(0,255)) for _ in range(6)])
    #return "test-device"

def get_random_power():
    return numpy.random.normal(150)

class LimitedList(list):
    def __init__(self, max_size = 1024, drop_data=True, *args, **kwargs):
        self.max_size = max_size
        self.drop_data = drop_data
        super().__init__(*args, **kwargs)
    
    def append(self, item):
        if sys.getsizeof(self) + sys.getsizeof(item) > self.max_size:
            if self.drop_data:
                super().pop(0)
            else:
                raise Exception('Not enough memory.')
        
        super().append(item)
    
    def bsize(self):
        return sys.getsizeof(self)

# ====MQTT Functions====
def on_connect(client, userdata, flags, rc):
    print("connected")
    device = userdata['device']
    topic = (settings.TOPICS['server_control']).format(device_id = device.device_id)
    client.subscribe(topic, qos=0)

def on_message(client, userdata, msg):
    print("received message")
    device = userdata['device']
    match msg.topic:
        case device.control_topic:
            device.accept_server_control(msg)
# ========================

class Device:
    mqtt_client = None
    def __init__(self, verbose_opt=False):
        self.verbose_opt = verbose_opt
        self.device_on = True
        self.relay_on = False
        self.power_measure_history = LimitedList()
        self.device_id = get_random_id()
        self.sample_rate = 1

        self.lobby_topic = settings.TOPICS['devices_lobby']
        self.data_topic = (settings.TOPICS['device_data']).format(device_id = self.device_id)
        self.feedback_topic = (settings.TOPICS['device_feedback']).format(device_id = self.device_id)
        self.control_topic = (settings.TOPICS['server_control']).format(device_id = self.device_id)
        # self.server_feedback_topic = (mqtt_settings.TOPICS['server_feedback']).format(device_id = self.device_id)        

    def __del__(self):
        self.device_on = False
        if self.mqtt_client:
            self.mqtt_client.loop_stop()
            self.mqtt_client.disconnect()
    
    def start_mqtt_client(self):
        self.mqtt_client = mqtt.Client(userdata={'device':self})
        self.mqtt_client.on_connect = on_connect
        self.mqtt_client.on_message = on_message
        self.mqtt_client.connect(settings.BROKER, settings.PORT, settings.KEEP_ALIVE)
        self.mqtt_client.loop_start()

    def register_device(self):
        if self.verbose_opt: print(f"Device ID: {self.device_id}")
        msg = { 'register_device':self.device_id }
        self.mqtt_client.publish(self.lobby_topic, payload=json.dumps(msg), qos=0, retain=False)

    #def associate_user(self, user_id):
    #    msg = { 'associate_user': {'user':user_id, 'device':self.device_id } }
    #    self.mqtt_client.publish(self.lobby_topic, payload=json.dumps(msg), qos=0, retain=False)

    def set_on_off(self, state):
        if self.verbose_opt: print(f"Device {self.device_id}: {state}")
        self.relay_on = state

    def feedback(self, msg):
        print(msg)
        self.mqtt_client.publish(self.feedback_topic, payload=json.dumps(msg, default = str), qos=0, retain=False)

    def register_power(self):
        registry = { 'ts': datetime.datetime.now(), 'pw':get_random_power() }
        self.power_measure_history.append( registry )

    def broadcast_power(self, size=1):
        self.mqtt_client.publish(self.data_topic, \
            payload=json.dumps(self.power_measure_history[-size], default = str), \
                 qos=0, retain=False)

    def set_sample_rate(self, new_rate):
        self.sample_rate = new_rate

    #def resample_history(self, new_rate):
    #    pass

    def accept_server_control(self, msg):
        payload = json.loads(msg.payload)
        if self.verbose_opt: print(msg.topic, payload)

        match payload['command']:
            case 'set_on_off':
                self.set_on_off( payload['value'] )
        
        comm_feedback = {'id':payload['id'], 'recv_ts': datetime.datetime.now()}
        self.feedback(comm_feedback)

    def device_loop(self):
        while self.device_on:
            self.register_power()
            self.broadcast_power()
            time.sleep(1/self.sample_rate)

if __name__ == '__main__':
    device = Device(verbose_opt=True)
    # start device loop:
    device.start_mqtt_client()
    device.register_device() # shouldn't be done every time, we need a local file to save the info that device is registered
    device.device_loop()