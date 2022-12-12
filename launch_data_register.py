import threading
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from mqtt_handler import DataRegister
from settings import DB_ENGINE

engine = create_engine(DB_ENGINE)
Session = sessionmaker(bind = engine)
session = Session()

handler = DataRegister(session, verbose_opt=True)
# creates a thread to the mqtt_client, so the server is free to do other tasks
threading.Thread( target=handler.start_mqtt_client ).start()