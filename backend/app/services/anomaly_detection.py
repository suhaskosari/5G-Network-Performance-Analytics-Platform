import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from typing import List, Tuple, Dict
from datetime import datetime, timedelta
from app.models import NetworkKPI, AnomalyResult

class AnomalyDetector:
    """Multi-method anomaly detection for 5G network KPIs"""
    
    def __init__(self):
        self.isolation_forest = IsolationForest(
            contamination=0.05,
            random_state=42,
            n_estimators=100
        )
        self.baseline_stats = {}
    
    def z_score_detection(
        self, 
        data: pd.Series, 
        threshold: float = 3.0
    ) -> Tuple[np.ndarray, np.ndarray]:
        """Detect anomalies using z-score method"""
        mean = data.mean()
        std = data.std()
        
        if std == 0:
            return np.zeros(len(data), dtype=bool), np.zeros(len(data))
        
        z_scores = np.abs((data - mean) / std)
        anomalies = z_scores > threshold
        
        return anomalies, z_scores
    
    def rolling_baseline_detection(
        self,
        data: pd.Series,
        window_size: int = 50,
        threshold_multiplier: float = 2.5
    ) -> Tuple[np.ndarray, pd.Series]:
        """Detect anomalies using rolling baseline with dynamic thresholds"""
        rolling_mean = data.rolling(window=window_size, min_periods=1).mean()
        rolling_std = data.rolling(window=window_size, min_periods=1).std()
        
        rolling_std = rolling_std.replace(0, 1e-6)
        
        deviations = np.abs(data - rolling_mean) / rolling_std
        anomalies = deviations > threshold_multiplier
        
        return anomalies.values, deviations
    
    def isolation_forest_detection(
        self,
        data: pd.DataFrame,
        features: List[str]
    ) -> Tuple[np.ndarray, np.ndarray]:
        """Detect anomalies using Isolation Forest on multiple features"""
        X = data[features].values
        
        predictions = self.isolation_forest.fit_predict(X)
        scores = self.isolation_forest.score_samples(X)
        
        anomalies = predictions == -1
        
        return anomalies, scores
    
    def detect_latency_spikes(
        self,
        kpis: List[NetworkKPI],
        method: str = "z_score",
        threshold: float = 3.0
    ) -> List[AnomalyResult]:
        """Detect latency spikes in KPI stream"""
        if not kpis:
            return []
        
        df = pd.DataFrame([{
            'timestamp': kpi.timestamp,
            'cell_id': kpi.cell_id,
            'latency_ms': kpi.latency_ms,
            'throughput_mbps': kpi.throughput_mbps,
            'packet_loss_pct': kpi.packet_loss_pct
        } for kpi in kpis])
        
        results = []
        
        for cell_id, group in df.groupby('cell_id'):
            group = group.sort_values('timestamp')
            latency = group['latency_ms']
            
            if method == "z_score":
                anomalies, scores = self.z_score_detection(latency, threshold)
                baseline = latency.mean()
                
            elif method == "rolling":
                anomalies, scores = self.rolling_baseline_detection(latency)
                baseline = latency.rolling(window=50, min_periods=1).mean().iloc[-1]
                
            elif method == "isolation_forest":
                anomalies, scores = self.isolation_forest_detection(
                    group, 
                    ['latency_ms', 'throughput_mbps', 'packet_loss_pct']
                )
                baseline = None
            
            for idx, (_, row) in enumerate(group.iterrows()):
                if anomalies[idx]:
                    results.append(AnomalyResult(
                        timestamp=row['timestamp'],
                        cell_id=cell_id,
                        metric='latency_ms',
                        value=row['latency_ms'],
                        is_anomaly=True,
                        anomaly_score=float(scores[idx]),
                        method=method,
                        threshold=threshold if method != "isolation_forest" else None,
                        baseline=baseline
                    ))
        
        return results
    
    def detect_throughput_drops(
        self,
        kpis: List[NetworkKPI],
        drop_threshold_pct: float = 30.0
    ) -> List[AnomalyResult]:
        """Detect sudden throughput drops"""
        if not kpis:
            return []
        
        df = pd.DataFrame([{
            'timestamp': kpi.timestamp,
            'cell_id': kpi.cell_id,
            'throughput_mbps': kpi.throughput_mbps
        } for kpi in kpis])
        
        results = []
        
        for cell_id, group in df.groupby('cell_id'):
            group = group.sort_values('timestamp')
            throughput = group['throughput_mbps'].values
            
            for i in range(20, len(throughput)):
                baseline = np.mean(throughput[i-20:i])
                current = throughput[i]
                drop_pct = ((baseline - current) / baseline) * 100
                
                if drop_pct > drop_threshold_pct:
                    results.append(AnomalyResult(
                        timestamp=group.iloc[i]['timestamp'],
                        cell_id=cell_id,
                        metric='throughput_mbps',
                        value=current,
                        is_anomaly=True,
                        anomaly_score=drop_pct,
                        method='throughput_drop',
                        threshold=drop_threshold_pct,
                        baseline=baseline
                    ))
        
        return results
    
    def detect_traffic_instability(
        self,
        kpis: List[NetworkKPI],
        window_minutes: int = 5
    ) -> List[AnomalyResult]:
        """Detect traffic instability using coefficient of variation"""
        if not kpis:
            return []
        
        df = pd.DataFrame([{
            'timestamp': kpi.timestamp,
            'cell_id': kpi.cell_id,
            'throughput_mbps': kpi.throughput_mbps,
            'latency_ms': kpi.latency_ms
        } for kpi in kpis])
        
        results = []
        
        for cell_id, group in df.groupby('cell_id'):
            group = group.sort_values('timestamp')
            group.set_index('timestamp', inplace=True)
            
            for metric in ['throughput_mbps', 'latency_ms']:
                rolling_mean = group[metric].rolling(f'{window_minutes}T').mean()
                rolling_std = group[metric].rolling(f'{window_minutes}T').std()
                
                cv = (rolling_std / rolling_mean) * 100
                
                instability_threshold = 50.0 if metric == 'throughput_mbps' else 40.0
                
                for timestamp, cv_value in cv.items():
                    if cv_value > instability_threshold:
                        results.append(AnomalyResult(
                            timestamp=timestamp,
                            cell_id=cell_id,
                            metric=f'{metric}_instability',
                            value=cv_value,
                            is_anomaly=True,
                            anomaly_score=cv_value,
                            method='traffic_instability',
                            threshold=instability_threshold,
                            baseline=None
                        ))
        
        return results
    
    def analyze_kpi_stream(
        self,
        kpis: List[NetworkKPI]
    ) -> Dict[str, List[AnomalyResult]]:
        """Run comprehensive anomaly detection on KPI stream"""
        return {
            'latency_spikes_zscore': self.detect_latency_spikes(kpis, method='z_score'),
            'latency_spikes_rolling': self.detect_latency_spikes(kpis, method='rolling'),
            'latency_spikes_ml': self.detect_latency_spikes(kpis, method='isolation_forest'),
            'throughput_drops': self.detect_throughput_drops(kpis),
            'traffic_instability': self.detect_traffic_instability(kpis)
        }