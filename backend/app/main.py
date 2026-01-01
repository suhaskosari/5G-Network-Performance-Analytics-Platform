from fastapi import FastAPI, HTTPException, Depends, Query, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timedelta
import pandas as pd
import uuid

from app.database import (
    get_db, init_db, write_kpi_to_influx, write_kpis_batch_to_influx,
    query_kpis_from_influx, AlertDB
)
from app.models import (
    NetworkKPI, KPIBatch, KPIQuery, StatisticalSummary, 
    AnomalyResult, Alert, AlertSeverity, TrafficProfile
)
from app.services.anomaly_detection import AnomalyDetector
from app.services.data_generator import NetworkKPIGenerator

app = FastAPI(
    title="5G Network Performance Analytics Platform",
    description="Real-time 5G network KPI ingestion, analysis, and anomaly detection",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    init_db()

anomaly_detector = AnomalyDetector()
kpi_generator = NetworkKPIGenerator(seed=42)

@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.utcnow()}

@app.post("/api/v1/kpis/ingest")
async def ingest_single_kpi(kpi: NetworkKPI, background_tasks: BackgroundTasks):
    try:
        background_tasks.add_task(write_kpi_to_influx, kpi)
        return {
            "status": "success",
            "message": "KPI ingested successfully",
            "timestamp": kpi.timestamp,
            "cell_id": kpi.cell_id
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to ingest KPI: {str(e)}")

@app.post("/api/v1/kpis/ingest/batch")
async def ingest_kpi_batch(batch: KPIBatch, background_tasks: BackgroundTasks):
    try:
        background_tasks.add_task(write_kpis_batch_to_influx, batch.kpis)
        return {
            "status": "success",
            "message": f"Batch of {len(batch.kpis)} KPIs ingested successfully",
            "source": batch.source,
            "count": len(batch.kpis)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to ingest batch: {str(e)}")

@app.post("/api/v1/generate/synthetic")
async def generate_synthetic_data(
    cell_ids: List[str] = Query(default=["gNB_001_Cell_1", "gNB_002_Cell_1"]),
    traffic_profiles: List[TrafficProfile] = Query(default=[TrafficProfile.EMBB]),
    duration_hours: float = Query(default=1.0, ge=0.1, le=24),
    anomaly_rate: float = Query(default=0.05, ge=0, le=0.5),
    background_tasks: BackgroundTasks = None
):
    try:
        start_time = datetime.utcnow() - timedelta(hours=duration_hours)
        
        kpis = kpi_generator.generate_kpi_stream(
            cell_ids=cell_ids,
            traffic_profiles=traffic_profiles,
            start_time=start_time,
            duration_hours=duration_hours,
            interval_seconds=10,
            anomaly_rate=anomaly_rate
        )
        
        background_tasks.add_task(write_kpis_batch_to_influx, kpis)
        
        return {
            "status": "success",
            "message": f"Generated {len(kpis)} synthetic KPI measurements",
            "cell_ids": cell_ids,
            "traffic_profiles": [tp.value for tp in traffic_profiles],
            "duration_hours": duration_hours,
            "anomaly_rate": anomaly_rate,
            "kpi_count": len(kpis)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate data: {str(e)}")

@app.post("/api/v1/kpis/query")
async def query_kpis(query: KPIQuery):
    try:
        records = query_kpis_from_influx(
            cell_ids=query.cell_ids,
            start_time=query.start_time,
            end_time=query.end_time,
            metrics=query.metrics
        )
        return records
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Query failed: {str(e)}")

@app.get("/api/v1/analytics/summary")
async def get_statistical_summary(
    cell_ids: Optional[List[str]] = Query(None),
    start_time: Optional[datetime] = Query(None),
    end_time: Optional[datetime] = Query(None)
):
    try:
        records = query_kpis_from_influx(
            cell_ids=cell_ids,
            start_time=start_time or datetime.utcnow() - timedelta(hours=1),
            end_time=end_time or datetime.utcnow()
        )
        
        if not records:
            return []
        
        df = pd.DataFrame(records)
        summaries = []
        
        for (cell_id, metric), group in df.groupby(['cell_id', 'metric']):
            values = group['value'].values
            
            summary = StatisticalSummary(
                metric=metric,
                cell_id=cell_id,
                traffic_profile=group['traffic_profile'].iloc[0] if 'traffic_profile' in group else TrafficProfile.MIXED,
                mean=float(values.mean()),
                median=float(pd.Series(values).median()),
                std_dev=float(values.std()),
                min=float(values.min()),
                max=float(values.max()),
                p95=float(pd.Series(values).quantile(0.95)),
                p99=float(pd.Series(values).quantile(0.99)),
                sample_count=len(values),
                time_range=f"{start_time or 'N/A'} to {end_time or 'N/A'}"
            )
            summaries.append(summary)
        
        return summaries
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Summary generation failed: {str(e)}")

@app.post("/api/v1/anomaly/detect")
async def detect_anomalies(
    cell_ids: Optional[List[str]] = Query(None),
    start_time: Optional[datetime] = Query(None),
    end_time: Optional[datetime] = Query(None),
    detection_methods: List[str] = Query(default=["z_score", "rolling"])
):
    try:
        records = query_kpis_from_influx(
            cell_ids=cell_ids,
            start_time=start_time or datetime.utcnow() - timedelta(hours=1),
            end_time=end_time or datetime.utcnow(),
            metrics=['latency_ms', 'throughput_mbps', 'packet_loss_pct']
        )
        
        if not records:
            return []
        
        df = pd.DataFrame(records)
        kpi_data = []
        
        for (cell_id, timestamp), group in df.groupby(['cell_id', 'time']):
            kpi_dict = {
                'timestamp': timestamp,
                'cell_id': cell_id,
                'traffic_profile': group['traffic_profile'].iloc[0] if 'traffic_profile' in group else 'Mixed'
            }
            
            for _, row in group.iterrows():
                kpi_dict[row['metric']] = row['value']
            
            if all(k in kpi_dict for k in ['latency_ms', 'throughput_mbps', 'packet_loss_pct']):
                kpi_data.append(NetworkKPI(**kpi_dict))
        
        all_anomalies = []
        
        if "z_score" in detection_methods:
            all_anomalies.extend(anomaly_detector.detect_latency_spikes(kpi_data, method='z_score'))
        
        if "rolling" in detection_methods:
            all_anomalies.extend(anomaly_detector.detect_latency_spikes(kpi_data, method='rolling'))
        
        all_anomalies.extend(anomaly_detector.detect_throughput_drops(kpi_data))
        
        return all_anomalies
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Anomaly detection failed: {str(e)}")

@app.post("/api/v1/alerts")
async def create_alert(alert: Alert, db: Session = Depends(get_db)):
    try:
        alert.id = str(uuid.uuid4())
        
        db_alert = AlertDB(
            id=alert.id,
            timestamp=alert.timestamp,
            cell_id=alert.cell_id,
            severity=alert.severity,
            metric=alert.metric,
            current_value=alert.current_value,
            threshold_value=alert.threshold_value,
            message=alert.message,
            acknowledged=alert.acknowledged
        )
        
        db.add(db_alert)
        db.commit()
        db.refresh(db_alert)
        
        return alert
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create alert: {str(e)}")

@app.get("/api/v1/alerts")
async def get_alerts(
    cell_id: Optional[str] = None,
    severity: Optional[AlertSeverity] = None,
    acknowledged: Optional[bool] = None,
    limit: int = Query(default=100, le=1000),
    db: Session = Depends(get_db)
):
    try:
        query = db.query(AlertDB)
        
        if cell_id:
            query = query.filter(AlertDB.cell_id == cell_id)
        if severity:
            query = query.filter(AlertDB.severity == severity)
        if acknowledged is not None:
            query = query.filter(AlertDB.acknowledged == acknowledged)
        
        alerts = query.order_by(AlertDB.timestamp.desc()).limit(limit).all()
        
        return [Alert(
            id=a.id,
            timestamp=a.timestamp,
            cell_id=a.cell_id,
            severity=a.severity,
            metric=a.metric,
            current_value=a.current_value,
            threshold_value=a.threshold_value,
            message=a.message,
            acknowledged=a.acknowledged
        ) for a in alerts]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve alerts: {str(e)}")

@app.get("/api/v1/status")
async def get_system_status(db: Session = Depends(get_db)):
    try:
        active_alerts = db.query(AlertDB).filter(AlertDB.acknowledged == False).count()
        total_alerts = db.query(AlertDB).count()
        
        recent_kpis = query_kpis_from_influx(
            start_time=datetime.utcnow() - timedelta(hours=1)
        )
        
        return {
            "status": "operational",
            "timestamp": datetime.utcnow(),
            "statistics": {
                "active_alerts": active_alerts,
                "total_alerts": total_alerts,
                "recent_kpis_count": len(recent_kpis),
                "time_window": "last_1_hour"
            }
        }
    except Exception as e:
        return {
            "status": "degraded",
            "error": str(e),
            "timestamp": datetime.utcnow()
        }