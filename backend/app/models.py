from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List
from enum import Enum

class TrafficProfile(str, Enum):
    EMBB = "eMBB"  # Enhanced Mobile Broadband
    URLLC = "URLLC"  # Ultra-Reliable Low-Latency
    MMTC = "mMTC"  # Massive Machine-Type Communications
    MIXED = "Mixed"

class AlertSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"

class NetworkKPI(BaseModel):
    timestamp: datetime
    cell_id: str = Field(..., description="gNodeB cell identifier")
    traffic_profile: TrafficProfile
    
    # Core 5G KPIs
    latency_ms: float = Field(..., ge=0, description="End-to-end latency in milliseconds")
    throughput_mbps: float = Field(..., ge=0, description="Throughput in Mbps")
    packet_loss_pct: float = Field(..., ge=0, le=100, description="Packet loss percentage")
    
    # Additional metrics
    jitter_ms: Optional[float] = Field(None, ge=0, description="Jitter in milliseconds")
    signal_strength_dbm: Optional[float] = Field(None, description="Signal strength in dBm")
    active_users: Optional[int] = Field(None, ge=0, description="Number of active UEs")
    
    class Config:
        json_schema_extra = {
            "example": {
                "timestamp": "2025-01-15T10:30:00Z",
                "cell_id": "gNB_001_Cell_1",
                "traffic_profile": "eMBB",
                "latency_ms": 15.5,
                "throughput_mbps": 850.2,
                "packet_loss_pct": 0.05,
                "jitter_ms": 2.1,
                "signal_strength_dbm": -75.0,
                "active_users": 45
            }
        }

class KPIBatch(BaseModel):
    kpis: List[NetworkKPI]
    source: str = Field(default="synthetic", description="Data source identifier")

class AnomalyResult(BaseModel):
    timestamp: datetime
    cell_id: str
    metric: str
    value: float
    is_anomaly: bool
    anomaly_score: float
    method: str
    threshold: Optional[float] = None
    baseline: Optional[float] = None

class Alert(BaseModel):
    id: Optional[str] = None
    timestamp: datetime
    cell_id: str
    severity: AlertSeverity
    metric: str
    current_value: float
    threshold_value: float
    message: str
    acknowledged: bool = False

class KPIQuery(BaseModel):
    cell_ids: Optional[List[str]] = None
    traffic_profiles: Optional[List[TrafficProfile]] = None
    start_time: datetime
    end_time: datetime
    metrics: Optional[List[str]] = None

class StatisticalSummary(BaseModel):
    metric: str
    cell_id: str
    traffic_profile: TrafficProfile
    mean: float
    median: float
    std_dev: float
    min: float
    max: float
    p95: float
    p99: float
    sample_count: int
    time_range: str