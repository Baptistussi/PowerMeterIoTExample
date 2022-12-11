import time
import threading
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from mqtt_handler import DeviceCommander
from settings import DB_FILE

engine = create_engine(f"sqlite:///{DB_FILE}")
Session = sessionmaker(bind = engine)
session = Session()

handler = DeviceCommander(session, verbose_opt=True)
# creates a thread to the mqtt_client, so the server is free to do other tasks
threading.Thread( target=handler.start_mqtt_client ).start()
time.sleep(1)
handler.load_devices_from_db()
threading.Thread( target=handler.check_expired_commands ).start()