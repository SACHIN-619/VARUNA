"""
VARUNA Dataset Registry ORM Model.
SIH 2026 Problem Statement: SIH26081

Tracks every raw and processed meteorological dataset ingested into VARUNA,
preserving verifiable provenance, SHA256 checksums, temporal/spatial bounds, and format metadata.
"""

from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, Integer, JSON, Text, BigInteger
from app.core.database import Base

class DatasetRegistry(Base):
    __tablename__ = "dataset_registry"

    dataset_id = Column(String(100), primary_key=True)
    name = Column(String(255), nullable=False)
    source = Column(String(100), nullable=False)  # e.g., NCMRWF, NOAA, IMD, ECMWF
    version = Column(String(50), nullable=False, default="v1.0")
    license = Column(String(100), default="Open Data / MoES Research")
    format = Column(String(50), nullable=False)  # CSV, JSON, JSONL, PARQUET, NETCDF, GRIB2, GEOJSON, ZIP
    variables = Column(JSON, nullable=False)  # ["rainfall", "temperature", "wind_speed"]
    spatial_coverage = Column(String(100), nullable=False, default="INDIA_ALL_SUBDIVISIONS")
    temporal_coverage_start = Column(DateTime, nullable=True)
    temporal_coverage_end = Column(DateTime, nullable=True)
    resolution = Column(String(50), nullable=False, default="12km")
    ingestion_timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    checksum = Column(String(64), nullable=True)  # SHA-256
    record_count = Column(BigInteger, default=0)
    file_path = Column(String(500), nullable=True)
    status = Column(String(50), default="AVAILABLE")  # AVAILABLE, INGESTING, FAILED, ARCHIVED
    provenance_badge = Column(String(50), default="PUBLIC_BENCHMARK")  # PUBLIC_BENCHMARK | SYNTHETIC_STRESS_TEST | AUTHORIZED_OPERATIONAL_FEED
    metadata_json = Column(JSON, nullable=True)
