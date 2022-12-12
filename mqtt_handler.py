import time
import json
import datetime
import paho.mqtt.client as mqtt

from models import User, Device, DataEntry, ControlEntry
import settings

def date_hook(json_dict):
    # data looks like: {'ts': datetime.datetime(2022, 12, 4, 2, 1, 42, 225836), 'pw': 148.12556594730796}
    for (key, value) in json_dict.items():
        try:
            json_dict[key] = datetime.datetime.strptime(value, "%Y-%m-%d %H:%M:%S.%f")
        except:
            pass
    return json_dict

class MqttHandler:
    @staticmethod
    def on_connect(client, userdata, flags, rc):
        print("connected")
        topic = (settings.TOPICS['devices_lobby'])
        client.subscribe(topic, qos=0)

    def __init__(self, db_session, verbose_opt=False):
        self.db_session = db_session
        self.verbose_opt = verbose_opt
    
    def start_mqtt_client(self):
        self.mqtt_client = mqtt.Client(userdata={'handler':self})
        self.mqtt_client.on_connect = self.on_connect
        self.mqtt_client.on_message = self.on_message
        self.mqtt_client.connect(settings.BROKER, settings.PORT, settings.KEEP_ALIVE)
        self.mqtt_client.loop_forever()
    
    def __del__(self):
        if self.mqtt_client:
            self.mqtt_client.loop_stop()
            self.mqtt_client.disconnect()
            self.db_session.close()

class DataRegister(MqttHandler):
    @staticmethod
    def on_message(client, userdata, msg):
        #print("received message")
        handler = userdata['handler']
        if  msg.topic == settings.TOPICS['devices_lobby']:
            # CODE FROM DEVICE: msg = { 'register_device':self.device_id }
            device_id = json.loads(msg.payload)['register_device']
            handler.register_device(device_id)
        elif settings.TOPICS['device_data'].format(device_id='') in msg.topic:
            # it's a device data topic
            device_id = msg.topic.split(settings.TOPICS['device_data'].format(device_id=''))[1]
            handler.register_data(device_id, msg.payload)
    
    def register_device(self, device_id):
        data_topic = settings.TOPICS['device_data'].format(device_id=device_id)
        self.mqtt_client.subscribe(data_topic)
        self.db_session.add( Device(device_id=device_id) )
        self.db_session.commit()
        if self.verbose_opt: print(f"Registered {device_id}")
    
    def load_devices_from_db(self):
        for row in self.db_session.query(Device).all():
            data_topic = settings.TOPICS['device_data'].format(device_id=row.device_id)
            self.mqtt_client.subscribe(data_topic)
            if self.verbose_opt: print(f"Loaded {row.device_id}")

    #def associate_user(user_id, device_id):
    #    pass

    def register_data(self, device_id, payload):
        data = json.loads(payload, object_hook=date_hook)
        # data looks like: ['2022-12-04 01:26:43.573346', 149.4411883802525]
        self.db_session.add( DataEntry(timestamp=data['ts'], measure=data['pw'], device_id=device_id) )
        self.db_session.commit()

class DeviceCommander(MqttHandler):
    MAX_COMMANDS = 10000
    COMMAND_TIMEOUT = 3

    @staticmethod
    def on_message(client, userdata, msg):
        # print("received message")
        handler = userdata['handler']
        if settings.TOPICS['device_feedback'].format(device_id='') in msg.topic:
            # it's a device feedback topic
            handler.register_command_feedback(payload=msg.payload)

    def __init__(self, db_session, verbose_opt=False):
        super().__init__(db_session, verbose_opt)
        self.commands_waiting_feedback = dict()
        self.commands_expiration_queue = list()
        self.last_command_id = 0
    
    def load_devices_from_db(self):
        self.device_list = self.db_session.query(Device).all()
        for row in self.device_list:
            feedback_topic = settings.TOPICS['device_feedback'].format(device_id=row.device_id)
            self.mqtt_client.subscribe(feedback_topic)
            if self.verbose_opt: print(f"Loaded {row.device_id}")
    
    def get_command_id(self):
        self.last_command_id += 1
        self.last_command_id %= self.MAX_COMMANDS
        return self.last_command_id

    def send_command(self, device_id, command_type, value):
        payload = {'id': self.get_command_id(),'command': command_type, 'value': value}
        control_topic = settings.TOPICS['server_control'].format(device_id=device_id)
        self.mqtt_client.publish(control_topic, payload=json.dumps(payload), qos=0, retain=False)
        # after sending, save it to commands waiting feedback, with some extra information for later use when registering feedback
        payload['order_ts'] = datetime.datetime.now()
        payload['device_id'] = device_id
        self.commands_expiration_queue.append( (payload['id'], payload['order_ts']) )
        self.commands_waiting_feedback[payload.pop('id')] = payload
    
    def register_command_feedback(self, payload=None, command_id=-1, failure=False):
        if failure: # normally, in case of failure, this function is called by check_expired_commands
            command_to_register = self.commands_waiting_feedback.pop(command_id)
        else: # on non-failure cases, this function is called by on_message
            data = json.loads(payload, object_hook=date_hook)
            print(data)
            # payload looks like {'id':payload['id'], 'recv_ts': datetime.datetime.now()}
            # removes command from the waiting dict
            command_to_register = self.commands_waiting_feedback.pop(data['id'])
            # finds the command in the queue and removes it:
            for command in self.commands_expiration_queue:
                if command[0] == data['id']:
                    self.commands_expiration_queue.remove(command)
        # write the command to db
        recv_ts = data['recv_ts'] if not failure else None
        result = not failure

        self.db_session.add( ControlEntry(
            order_timestamp = command_to_register['order_ts'],
            feedback_timestamp = recv_ts,
            command_type = command_to_register['command'],
            value = command_to_register['value'],
            result = result,
            device_id = command_to_register['device_id']
        ) )
        self.db_session.commit()

    def check_expired_commands(self):
        "removes old commands from the front of the queue"
        while True:
            if len(self.commands_expiration_queue) == 0:
                pass
            elif ( datetime.datetime.now() - self.commands_expiration_queue[0][1] ).seconds > self.COMMAND_TIMEOUT:
                print('Command timeout.')
                self.register_command_feedback( command_id=self.commands_expiration_queue.pop(0)[0], failure=True )