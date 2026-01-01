from sqlalchemy import create_engine, Column, String, Float, DateTime, Integer, Boolean, Enum as SQLEnum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS
import os
from datetime import datetime
from typing import List, Optional
from app.models import NetworkKPI, TrafficProfile, Alert, AlertSeverity

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/network_analytics")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

INFLUX_URL = os.getenv("INFLUX_URL", "http://localhost:8086")
INFLUX_TOKEN = os.getenv("INFLUX_TOKEN", "my-token")
INFLUX_ORG = os.getenv("INFLUX_ORG", "5g-analytics")
INFLUX_BUCKET = os.getenv("INFLUX_BUCKET", "network-kpis")

influx_client = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG)
write_api = influx_client.write_api(write_options=SYNCHRONOUS)
query_api = influx_client.query_api()

class AlertDB(Base):
    __tablename__ = "alerts"
    
    id = Column(String, primary_key=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    cell_id = Column(String, nullable=False, index=True)
    severity = Column(SQLEnum(AlertSeverity), nullable=False)
    metric = Column(String, nullable=False)
    current_value = Column(Float, nullable=False)
    threshold_value = Column(Float, nullable=False)
    message = Column(String, nullable=False)
    acknowledged = Column(Boolean, default=False)

class CellMetadata(Base):
    __tablename__ = "cell_metadata"
    
    cell_id = Column(String, primary_key=True)
    site_name = Column(String)
    latitude = Column(Float)
    longitude = Column(Float)
    frequency_band = Column(String)
    max_capacity_mbps = Column(Float)
    deployment_date = Column(DateTime)

def init_db():
    Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def write_kpi_to_influx(kpi: NetworkKPI):
    point = (
        Point("network_kpi")
        .tag("cell_id", kpi.cell_id)
        .tag("traffic_profile", kpi.traffic_profile.value)
        .field("latency_ms", float(kpi.latency_ms))
        .field("throughput_mbps", float(kpi.throughput_mbps))
        .field("packet_loss_pct", float(kpi.packet_loss_pct))
        .time(kpi.timestamp)
    )
    
    if kpi.jitter_ms is not None:
        point.field("jitter_ms", float(kpi.jitter_ms))
    if kpi.signal_strength_dbm is not None:
        point.field("signal_strength_dbm", float(kpi.signal_strength_dbm))
    if kpi.active_users is not None:
        point.field("active_users", kpi.active_users)
    
    write_api.write(bucket=INFLUX_BUCKET, org=INFLUX_ORG, record=point)

def write_kpis_batch_to_influx(kpis: List[NetworkKPI]):
    points = []
    for kpi in kpis:
        point = (
            Point("network_kpi")
            .tag("cell_id", kpi.cell_id)
            .tag("traffic_profile", kpi.traffic_profile.value)
            .field("latency_ms", float(kpi.latency_ms))
            .field("throughput_mbps", float(kpi.throughput_mbps))
            .field("packet_loss_pct", float(kpi.packet_loss_pct))
            .time(kpi.timestamp)
        )
        
        if kpi.jitter_ms is not None:
            point.field("jitter_ms", float(kpi.jitter_ms))
        if kpi.signal_strength_dbm is not None:
            point.field("signal_strength_dbm", float(kpi.signal_strength_dbm))
        if kpi.active_users is not None:
            point.field("active_users", kpi.active_users)
        
        points.append(point)
    
    write_api.write(bucket=INFLUX_BUCKET, org=INFLUX_ORG, record=points)

def query_kpis_from_influx(
    cell_ids: Optional[List[str]] = None,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    metrics: Optional[List[str]] = None
) -> List[dict]:
    
    query = f'from(bucket: "{INFLUX_BUCKET}")'
    
    if start_time and end_time:
        start_str = start_time.strftime("%Y-%m-%dT%H:%M:%SZ")
        end_str = end_time.strftime("%Y-%m-%dT%H:%M:%SZ")
        query += f' |> range(start: {start_str}, stop: {end_str})'
    elif start_time:
        start_str = start_time.strftime("%Y-%m-%dT%H:%M:%SZ")
        query += f' |> range(start: {start_str})'
    else:
        query += ' |> range(start: -1h)'
    
    query += ' |> filter(fn: (r) => r["_measurement"] == "network_kpi")'
    
    if cell_ids:
        cell_filter = ' or '.join([f'r["cell_id"] == "{cid}"' for cid in cell_ids])
        query += f' |> filter(fn: (r) => {cell_filter})'
    
    if metrics:
        metric_filter = ' or '.join([f'r["_field"] == "{m}"' for m in metrics])
        query += f' |> filter(fn: (r) => {metric_filter})'
    
    result = query_api.query(org=INFLUX_ORG, query=query)
    
    records = []
    for table in result:
        for record in table.records:
            records.append({
                'time': record.get_time(),
                'cell_id': record.values.get('cell_id'),
                'traffic_profile': record.values.get('traffic_profile'),
                'metric': record.get_field(),
                'value': record.get_value()
            })
    
    return records