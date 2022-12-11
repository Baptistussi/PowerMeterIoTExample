from datetime import datetime
from sqlalchemy import create_engine, Column, ForeignKey, Integer, String, Float, Boolean, TIMESTAMP
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base

engine = create_engine("sqlite:///powermeter.sqlite")

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    name = Column(String)
    email = Column(String)
    devices = relationship("Device")

class Device(Base):
    __tablename__ = 'devices'
    id = Column(Integer, primary_key=True)
    device_id = Column(String)
    owner_id = Column(Integer, ForeignKey("users.id"))
    data_entries = relationship("DataEntry")

class DataEntry(Base):
    __tablename__ = 'dataEntries'
    id = Column(Integer, primary_key=True)
    timestamp = Column(TIMESTAMP(timezone=False))
    measure = Column(Float)
    device_id = Column(Integer, ForeignKey("devices.id"))

class ControlEntry(Base):
    __tablename__ = 'controlEntries'
    id = Column(Integer, primary_key=True)
    order_timestamp = Column(TIMESTAMP(timezone=False))
    feedback_timestamp = Column(TIMESTAMP(timezone=False), default=datetime.now())
    command_type = Column(String)
    value = Column(String)
    result = Column(Boolean)
    device_id = Column(Integer, ForeignKey("devices.id"))

if __name__ == '__main__':
    Base.metadata.create_all(engine)