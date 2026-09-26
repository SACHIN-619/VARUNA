from sqlalchemy import Column, String, JSON
from app.core.database import Base

class Region(Base):
    __tablename__ = "regions"

    id = Column(String(50), primary_key=True)  # e.g. "IN_TELANGANA_HYDERABAD"
    name = Column(String(100), nullable=False)
    state = Column(String(100), nullable=False)
    country = Column(String(50), default="India", nullable=False)
    geometry = Column(JSON, nullable=True)  # GeoJSON representation compatible with GIS/PostGIS
    centroid = Column(JSON, nullable=True)  # {"lat": 17.3850, "lon": 78.4867}
    region_metadata = Column(JSON, nullable=True)  # terrain, agro-climatic zone, river basin
