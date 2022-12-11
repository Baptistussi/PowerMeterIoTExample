import time
import random
import threading
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session

from mqtt_handler import DeviceCommander
from settings import DB_FILE

engine = create_engine(f"sqlite:///{DB_FILE}")
session_factory = sessionmaker(bind=engine)
Session = scoped_session(session_factory)
session = Session()

handler = DeviceCommander(session, verbose_opt=False)
# creates a thread to the mqtt_client, so the server is free to do other tasks
threading.Thread( target=handler.start_mqtt_client ).start()
time.sleep(1)
handler.load_devices_from_db()
threading.Thread( target=handler.check_expired_commands ).start()

time.sleep(1) # just so the input isn't overwritten by the handler's messages
orders_p_s = int( input("Orders per second: ") )
last_time = time.time()
while True:
    if (time.time() - last_time) > (1./orders_p_s):
        last_time = time.time()
        device = random.choice( handler.device_list )
        handler.send_command(device.device_id, "set_on_off", random.randint(0,4) % 2)
