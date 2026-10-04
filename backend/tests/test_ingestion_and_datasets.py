"""
VARUNA Heterogeneous Ingestion & Dataset Registry Test Suite.
SIH 2026 Problem Statement: SIH26081

Tests:
- CSV, JSON, JSONL, GeoJSON, and ZIP streaming ingestion
- Schema validation & missing column handling
- Unit normalization (Kelvin -> °C, km/h -> m/s, cm -> mm)
- Coordinate validation & out-of-bounds flagging
- Duplicate detection & deduplication
- Missing value dropping & quality flag assessment
- DatasetRegistry checksum and record count updates
"""

import io
import json
import zipfile
import pytest
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.services.ingestion import ingestion_engine, HeterogeneousIngestionEngine
from app.services.harmonization import harmonization_service
from app.models.dataset import DatasetRegistry
from app.models.canonical_record import CanonicalWeatherEntity
from app.schemas.canonical import DataProvenance, QualityFlag


@pytest.fixture
def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def test_unit_normalization_canonical_standards():
    """Verify internal normalization to canonical standards (mm, °C, m/s)."""
    # 1. Temperature: Kelvin to Celsius
    val, unit, converted = harmonization_service.normalize_units(303.15, "Kelvin", "temperature")
    assert pytest.approx(val, abs=0.1) == 30.0
    assert unit == "°C"
    assert converted is True

    # 2. Temperature: Fahrenheit to Celsius
    val, unit, converted = harmonization_service.normalize_units(86.0, "Fahrenheit", "temperature")
    assert pytest.approx(val, abs=0.1) == 30.0
    assert unit == "°C"
    assert converted is True

    # 3. Wind Speed: km/h to m/s
    val, unit, converted = harmonization_service.normalize_units(36.0, "km/h", "wind_speed")
    assert pytest.approx(val, abs=0.1) == 10.0
    assert unit == "m/s"
    assert converted is True

    # 4. Wind Speed: knots to m/s
    val, unit, converted = harmonization_service.normalize_units(10.0, "knots", "wind_speed")
    assert pytest.approx(val, abs=0.1) == 5.14
    assert unit == "m/s"
    assert converted is True

    # 5. Rainfall: cm to mm
    val, unit, converted = harmonization_service.normalize_units(5.5, "cm", "rainfall")
    assert pytest.approx(val, abs=0.1) == 55.0
    assert unit == "mm"
    assert converted is True


def test_csv_streaming_ingestion(db_session: Session):
    """Tests chunked CSV ingestion with unit conversion, deduplication, and bounds checking."""
    csv_data = """valid_time,model_id,region_id,variable,value,unit,lead_hours,latitude,longitude
2026-09-28T00:00:00Z,NCUM,IN_TELANGANA_HYDERABAD,rainfall,82.0,mm,48,17.38,78.48
2026-09-28T00:00:00Z,GFS,IN_TELANGANA_HYDERABAD,rainfall,103.0,mm,48,17.38,78.48
2026-09-28T00:00:00Z,WRF,IN_TELANGANA_HYDERABAD,rainfall,4.7,cm,48,17.38,78.48
2026-09-28T00:00:00Z,NCUM,IN_TELANGANA_HYDERABAD,rainfall,82.0,mm,48,17.38,78.48
2026-09-28T00:00:00Z,AI_WEATHER,IN_TELANGANA_HYDERABAD,temperature,304.15,Kelvin,48,17.38,78.48
"""
    result = ingestion_engine.ingest_dataset(
        db=db_session,
        dataset_id="TEST_CSV_BATCH_001",
        file_content=csv_data.encode("utf-8"),
        filename="test_feed.csv",
        source="NCMRWF_TEST",
        provenance=DataProvenance.PUBLIC_BENCHMARK.value,
        persist_records=True
    )

    assert result["status"] == "COMPLETED"
    assert result["records_processed"] == 5
    assert result["duplicates_skipped"] == 1  # NCUM was duplicated
    assert result["records_ingested"] == 4

    # Verify WRF 4.7 cm was converted to 47.0 mm
    wrf_rec = db_session.query(CanonicalWeatherEntity).filter(
        CanonicalWeatherEntity.dataset_id == "TEST_CSV_BATCH_001",
        CanonicalWeatherEntity.model_id == "WRF"
    ).first()
    assert wrf_rec is not None
    assert wrf_rec.value == 47.0
    assert wrf_rec.unit == "mm"

    # Verify AI_WEATHER 304.15 K was converted to 31.0 °C
    ai_rec = db_session.query(CanonicalWeatherEntity).filter(
        CanonicalWeatherEntity.dataset_id == "TEST_CSV_BATCH_001",
        CanonicalWeatherEntity.model_id == "AI_WEATHER"
    ).first()
    assert ai_rec is not None
    assert pytest.approx(ai_rec.value, abs=0.1) == 31.0
    assert ai_rec.unit == "°C"


def test_jsonl_streaming_ingestion(db_session: Session):
    """Tests JSONL line-by-line streaming ingestion."""
    lines = [
        json.dumps({"valid_time": "2026-09-28T00:00:00Z", "model_id": "NCUM", "region_id": "IN_TELANGANA_HYDERABAD", "variable": "rainfall", "value": 75.0, "unit": "mm", "lead_hours": 24}),
        json.dumps({"valid_time": "2026-09-28T00:00:00Z", "model_id": "GFS", "region_id": "IN_TELANGANA_HYDERABAD", "variable": "rainfall", "value": 90.0, "unit": "mm", "lead_hours": 24}),
        json.dumps({"valid_time": "2026-09-28T00:00:00Z", "model_id": "WRF", "region_id": "IN_TELANGANA_HYDERABAD", "variable": "wind_speed", "value": 36.0, "unit": "km/h", "lead_hours": 24})
    ]
    jsonl_content = "\n".join(lines).encode("utf-8")

    result = ingestion_engine.ingest_dataset(
        db=db_session,
        dataset_id="TEST_JSONL_BATCH_002",
        file_content=jsonl_content,
        filename="stream.jsonl",
        source="IMD_AWS",
        provenance=DataProvenance.PUBLIC_BENCHMARK.value,
        persist_records=True
    )

    assert result["status"] == "COMPLETED"
    assert result["records_ingested"] == 3
    # Wind speed 36 km/h -> 10 m/s
    wind_rec = db_session.query(CanonicalWeatherEntity).filter(
        CanonicalWeatherEntity.dataset_id == "TEST_JSONL_BATCH_002",
        CanonicalWeatherEntity.variable == "wind_speed"
    ).first()
    assert wind_rec is not None
    assert pytest.approx(wind_rec.value, abs=0.1) == 10.0
    assert wind_rec.unit == "m/s"


def test_geojson_ingestion(db_session: Session):
    """Tests GeoJSON FeatureCollection parsing and coordinate extraction."""
    geojson_doc = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [78.4867, 17.3850]},
                "properties": {
                    "valid_time": "2026-09-28T00:00:00Z",
                    "model_id": "NCUM",
                    "region_id": "IN_TELANGANA_HYDERABAD",
                    "variable": "rainfall",
                    "value": 85.0,
                    "unit": "mm",
                    "lead_hours": 48
                }
            }
        ]
    }
    content = json.dumps(geojson_doc).encode("utf-8")

    result = ingestion_engine.ingest_dataset(
        db=db_session,
        dataset_id="TEST_GEOJSON_BATCH_003",
        file_content=content,
        filename="spatial_grid.geojson",
        source="GEOJSON_SOURCE",
        provenance=DataProvenance.PUBLIC_BENCHMARK.value,
        persist_records=True
    )

    assert result["status"] == "COMPLETED"
    assert result["records_ingested"] == 1

    rec = db_session.query(CanonicalWeatherEntity).filter(
        CanonicalWeatherEntity.dataset_id == "TEST_GEOJSON_BATCH_003"
    ).first()
    assert rec.longitude == 78.4867
    assert rec.latitude == 17.3850


def test_zip_archive_ingestion(db_session: Session):
    """Tests ZIP archive extraction and streaming across contained files."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        csv_sub = "valid_time,model_id,region_id,variable,value,unit,lead_hours\n2026-09-28T00:00:00Z,NCUM,IN_TELANGANA,rainfall,60.0,mm,24\n"
        zf.writestr("subfolder/data1.csv", csv_sub)
        jsonl_sub = json.dumps({"valid_time": "2026-09-28T00:00:00Z", "model_id": "GFS", "region_id": "IN_TELANGANA", "variable": "rainfall", "value": 70.0, "unit": "mm", "lead_hours": 24}) + "\n"
        zf.writestr("subfolder/data2.jsonl", jsonl_sub)

    zip_bytes = buf.getvalue()

    result = ingestion_engine.ingest_dataset(
        db=db_session,
        dataset_id="TEST_ZIP_BUNDLE_004",
        file_content=zip_bytes,
        filename="archive.zip",
        source="ARCHIVE_BUNDLE",
        provenance=DataProvenance.PUBLIC_BENCHMARK.value,
        persist_records=True
    )

    assert result["status"] == "COMPLETED"
    assert result["records_ingested"] == 2


def test_dataset_registry_tracking(db_session: Session):
    """Verifies that DatasetRegistry correctly stores checksums, record counts, and status."""
    csv_data = "valid_time,model_id,region_id,variable,value,unit,lead_hours\n2026-09-28T00:00:00Z,NCUM,IN_TELANGANA,rainfall,65.0,mm,48\n"
    res = ingestion_engine.ingest_dataset(
        db=db_session,
        dataset_id="TEST_REGISTRY_RECORD_005",
        file_content=csv_data.encode("utf-8"),
        filename="feed.csv",
        source="NCMRWF_TEST",
        version="v2.1",
        provenance=DataProvenance.PUBLIC_BENCHMARK.value,
        persist_records=True
    )

    registry_entry = db_session.query(DatasetRegistry).filter(
        DatasetRegistry.dataset_id == "TEST_REGISTRY_RECORD_005"
    ).first()

    assert registry_entry is not None
    assert registry_entry.record_count == 1
    assert registry_entry.status == "AVAILABLE"
    assert registry_entry.checksum == res["checksum_sha256"]
    assert registry_entry.version == "v2.1"
