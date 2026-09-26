from sqlalchemy import Column, String, Boolean, JSON
from app.core.database import Base

class WeatherModel(Base):
    __tablename__ = "weather_models"

    id = Column(String(50), primary_key=True)  # NCUM, GFS, WRF, AI_WEATHER
    name = Column(String(100), nullable=False)
    type = Column(String(50), nullable=False)  # NWP_NATIONAL, NWP_GLOBAL, NWP_REGIONAL, AI_ML
    provider = Column(String(100), nullable=False)  # NCMRWF, NOAA/NCEP, IMD, DeepMind/ECMWF
    resolution = Column(String(50), nullable=False)  # e.g., "12 km", "25 km", "3 km", "0.25 deg"
    description = Column(String(500), nullable=True)
    active = Column(Boolean, default=True, nullable=False)
    model_metadata = Column(JSON, nullable=True)
