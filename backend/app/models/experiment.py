import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, Float, Integer, JSON, Text
from app.core.database import Base

class ExperimentRun(Base):
    __tablename__ = "experiment_runs"

    id = Column(String(80), primary_key=True, default=lambda: f"EXP_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}")
    title = Column(String(255), nullable=False)
    executed_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    split_ratio = Column(Float, nullable=False, default=0.70)
    train_samples = Column(Integer, nullable=False)
    unseen_test_samples = Column(Integer, nullable=False)
    variable = Column(String(50), nullable=False, default="rainfall")
    provenance = Column(String(80), nullable=False, default="synthetic_temporal_benchmark")
    results_table = Column(JSON, nullable=False)  # [{method, mae, rmse, bias, corr, csi, pod, far, brier}]
    mae_reduction_vs_simple_avg_pct = Column(Float, nullable=False)
    mae_reduction_vs_heuristic_pct = Column(Float, nullable=False)
    scientific_summary = Column(JSON, nullable=False)
    markdown_report = Column(Text, nullable=True)
