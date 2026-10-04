"""
VARUNA Dataset Registry Service.
SIH 2026 Problem Statement: SIH26081

Manages registered meteorological datasets, tracks their verification status,
checksums, spatial/temporal coverage, and provenance badges.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.models.dataset import DatasetRegistry
from app.schemas.canonical import DataProvenance

# Verified canonical public and benchmark datasets pre-registered with factual availability
STANDARD_SEEDED_DATASETS = [
    {
        "dataset_id": "IMDAA_REANALYSIS_12KM",
        "name": "Indian Monsoon Data Assimilation and Analysis (IMDAA) 12km Reanalysis",
        "source": "NCMRWF / IMD / UK Met Office",
        "version": "v1.0-4DVAR",
        "license": "MoES Public Research License",
        "format": "NETCDF / CSV",
        "variables": ["rainfall", "temperature", "wind_speed"],
        "spatial_coverage": "INDIAN_MONSOON_REGION (0-45N, 30-120E)",
        "resolution": "12 km",
        "provenance_badge": DataProvenance.PUBLIC_BENCHMARK.value,
        "record_count": 500,
        "status": "AVAILABLE",
        "metadata_json": {
            "assimilation_method": "4D-Var",
            "cycle_frequency": "00Z, 12Z",
            "official_portal": "https://rds.ncmrwf.gov.in"
        }
    },
    {
        "dataset_id": "IMD_AWS_GROUND_NETWORK",
        "name": "IMD Surface Automatic Weather Station (AWS) In-situ Network",
        "source": "India Meteorological Department (IMD)",
        "version": "v2.2-QC",
        "license": "IMD Open Met Data Policy",
        "format": "CSV / JSON",
        "variables": ["rainfall", "temperature", "wind_speed"],
        "spatial_coverage": "INDIA_PAN_NATIONAL_AWS",
        "resolution": "Point Observation (Station Network)",
        "provenance_badge": DataProvenance.PUBLIC_BENCHMARK.value,
        "record_count": 350,
        "status": "AVAILABLE",
        "metadata_json": {
            "sensor_types": ["Tipping Bucket Rain Gauge", "Ultrasonic Anemometer", "PT100 RTD"]
        }
    },
    {
        "dataset_id": "SYNTHETIC_STRESS_TEST_MONSOON_2026",
        "name": "VARUNA Multi-Model Synthetic Stress Test & Failure Injection Benchmark",
        "source": "VARUNA Empirical Research Suite",
        "version": "v2026.1",
        "license": "SIH26081 Development Benchmark License",
        "format": "PARQUET / CSV / JSONL",
        "variables": ["rainfall", "temperature", "wind_speed"],
        "spatial_coverage": "14_INDIAN_METEOROLOGICAL_SUBDIVISIONS",
        "resolution": "Multi-Resolution (3km WRF to 25km GFS)",
        "provenance_badge": DataProvenance.SYNTHETIC_STRESS_TEST.value,
        "record_count": 500,
        "status": "AVAILABLE",
        "metadata_json": {
            "edge_cases": ["Heavy Monsoon Trough", "Cyclone Landfall Squall", "GFS Extreme Wet Bias", "WRF Mesoscale Convective Burst"]
        }
    },
    {
        "dataset_id": "NCMRWF_NCUM_OPERATIONAL_GRID",
        "name": "NCMRWF NCUM Global Operational Numerical Forecast Stream",
        "source": "National Centre for Medium Range Weather Forecasting (NCMRWF)",
        "version": "NCUM-G v13.0",
        "license": "MoES Restricted Operational",
        "format": "GRIB2 / NetCDF4",
        "variables": ["rainfall", "temperature", "wind_speed", "humidity", "pressure"],
        "spatial_coverage": "GLOBAL / SOUTH_ASIA_DOMAIN",
        "resolution": "12 km",
        "provenance_badge": DataProvenance.AUTHORIZED_OPERATIONAL_FEED.value,
        "record_count": 0,
        "status": "AUTHORIZED_PROVIDER_REQUIRED",
        "metadata_json": {
            "clearance_required": "MoES / NCMRWF High Performance Computing Gateway Authorization",
            "vpn_tunnel_active": False
        }
    }
]


class DatasetRegistryService:
    @staticmethod
    def seed_initial_datasets(db: Session):
        """Ensures standard benchmark and operational metadata records are present."""
        for ds in STANDARD_SEEDED_DATASETS:
            existing = db.query(DatasetRegistry).filter(DatasetRegistry.dataset_id == ds["dataset_id"]).first()
            if not existing:
                db.add(DatasetRegistry(
                    dataset_id=ds["dataset_id"],
                    name=ds["name"],
                    source=ds["source"],
                    version=ds["version"],
                    license=ds["license"],
                    format=ds["format"],
                    variables=ds["variables"],
                    spatial_coverage=ds["spatial_coverage"],
                    resolution=ds["resolution"],
                    record_count=ds["record_count"],
                    status=ds["status"],
                    provenance_badge=ds["provenance_badge"],
                    metadata_json=ds["metadata_json"],
                    ingestion_timestamp=datetime.now(timezone.utc)
                ))
        db.commit()

    @staticmethod
    def list_datasets(
        db: Session,
        status: Optional[str] = None,
        provenance: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        query = db.query(DatasetRegistry)
        if status:
            query = query.filter(DatasetRegistry.status == status.upper())
        if provenance:
            query = query.filter(DatasetRegistry.provenance_badge == provenance.upper())
        
        datasets = query.order_by(DatasetRegistry.ingestion_timestamp.desc()).all()
        return [
            {
                "dataset_id": d.dataset_id,
                "name": d.name,
                "source": d.source,
                "version": d.version,
                "license": d.license,
                "format": d.format,
                "variables": d.variables,
                "spatial_coverage": d.spatial_coverage,
                "temporal_coverage": {
                    "start": d.temporal_coverage_start.isoformat() if d.temporal_coverage_start else None,
                    "end": d.temporal_coverage_end.isoformat() if d.temporal_coverage_end else None
                },
                "resolution": d.resolution,
                "ingestion_timestamp": d.ingestion_timestamp.isoformat() if d.ingestion_timestamp else None,
                "checksum": d.checksum,
                "record_count": d.record_count,
                "status": d.status,
                "provenance_badge": d.provenance_badge,
                "metadata": d.metadata_json or {}
            }
            for d in datasets
        ]

    @staticmethod
    def get_dataset(db: Session, dataset_id: str) -> Optional[Dict[str, Any]]:
        d = db.query(DatasetRegistry).filter(DatasetRegistry.dataset_id == dataset_id).first()
        if not d:
            return None
        return {
            "dataset_id": d.dataset_id,
            "name": d.name,
            "source": d.source,
            "version": d.version,
            "license": d.license,
            "format": d.format,
            "variables": d.variables,
            "spatial_coverage": d.spatial_coverage,
            "temporal_coverage": {
                "start": d.temporal_coverage_start.isoformat() if d.temporal_coverage_start else None,
                "end": d.temporal_coverage_end.isoformat() if d.temporal_coverage_end else None
            },
            "resolution": d.resolution,
            "ingestion_timestamp": d.ingestion_timestamp.isoformat() if d.ingestion_timestamp else None,
            "checksum": d.checksum,
            "record_count": d.record_count,
            "status": d.status,
            "provenance_badge": d.provenance_badge,
            "metadata": d.metadata_json or {}
        }


dataset_registry_service = DatasetRegistryService()
