import json
import datetime
import paho.mqtt.client as mqtt
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from models import User, Device, DataEntry, ControlEntry
import mqtt_settings

engine = create_engine("sqlite:///powermeter.sqlite")
Session = sessionmaker(bind = engine)
session = Session()

# ====MQTT Functions====
def on_connect(client, userdata, flags, rc):
    print("connected")
    topic = (mqtt_settings.TOPICS['devices_lobby'])
    client.subscribe(topic, qos=0)

def on_message(client, userdata, msg):
    print("received message")
    handler = userdata['handler']
    if  msg.topic == mqtt_settings.TOPICS['devices_lobby']:
        # CODE FROM DEVICE: msg = { 'register_device':self.device_id }
        device_id = json.loads(msg.payload)['register_device']
        handler.register_device(device_id)
    elif mqtt_settings.TOPICS['device_data'].format(device_id='') in msg.topic:
        # it's a device data topic
        device_id = msg.topic.split(mqtt_settings.TOPICS['device_data'].format(device_id=''))[1]
        handler.register_data(device_id, msg.payload)
# ========================

def date_hook(json_dict):
    # data looks like: {'ts': datetime.datetime(2022, 12, 4, 2, 1, 42, 225836), 'pw': 148.12556594730796}
    for (key, value) in json_dict.items():
        try:
            json_dict[key] = datetime.datetime.strptime(value, "%Y-%m-%d %H:%M:%S.%f")
        except:
            pass
    return json_dict

class Handler:
    def __init__(self, db_session):
        self.db_session = db_session
    
    def start_mqtt_client(self):
        self.mqtt_client = mqtt.Client(userdata={'handler':self})
        self.mqtt_client.on_connect = on_connect
        self.mqtt_client.on_message = on_message
        self.mqtt_client.connect(mqtt_settings.BROKER, mqtt_settings.PORT, mqtt_settings.KEEP_ALIVE)
        self.mqtt_client.loop_forever()
    
    def __del__(self):
        if self.mqtt_client:
            self.mqtt_client.loop_stop()
            self.mqtt_client.disconnect()
    
    def register_device(self, device_id):
        data_topic = mqtt_settings.TOPICS['device_data'].format(device_id=device_id)
        feedback_topic = mqtt_settings.TOPICS['device_feedback'].format(device_id=device_id)
        self.mqtt_client.subscribe(data_topic)
        self.mqtt_client.subscribe(feedback_topic)
        self.db_session.add( Device(device_id=device_id) )
        self.db_session.commit()

    #def associate_user(user_id, device_id):
    #    pass

    def register_data(self, device, payload):
        data = json.loads(payload, object_hook=date_hook)
        # data looks like: ['2022-12-04 01:26:43.573346', 149.4411883802525]
        print(f"Device {device}: {data}")
        self.db_session.add( DataEntry(timestamp=data['ts'], measure=data['pw'], device_id=device) )
        self.db_session.commit()

    def send_command(self, device, command):
        pass

if __name__ == '__main__':
    handler = Handler(session)
    handler.start_mqtt_client()