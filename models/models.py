from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.ext.declarative import declarative_base
import datetime

Base = declarative_base()

class Consulta(Base):
    __tablename__ = "consultas"
    id = Column(Integer, primary_key=True, index=True)
    usuario = Column(String, index=True)
    mensaje = Column(String)
    respuesta = Column(String)
    fecha = Column(DateTime, default=datetime.datetime.utcnow)

class CacheConsulta(Base):
    __tablename__ = "cache_consultas"
    id = Column(Integer, primary_key=True, index=True)
    pregunta = Column(String, unique=True)
    respuesta = Column(String)

class Log(Base):
    __tablename__ = "logs"
    id = Column(Integer, primary_key=True, index=True)
    nivel = Column(String)  # INFO, ERROR, WARNING
    mensaje = Column(String)
    fecha = Column(DateTime, default=datetime.datetime.utcnow)
