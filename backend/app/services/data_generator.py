import numpy as np
from datetime import datetime, timedelta
from typing import List, Optional
from app.models import NetworkKPI, TrafficProfile
import random

class NetworkKPIGenerator:
    """Generate synthetic 5G network KPIs with realistic patterns and anomalies"""
    
    def __init__(self, seed: Optional[int] = None):
        if seed:
            np.random.seed(seed)
            random.seed(seed)
        
        self.profile_params = {
            TrafficProfile.EMBB: {
                'latency_mean': 20.0, 'latency_std': 5.0,
                'throughput_mean': 800.0, 'throughput_std': 150.0,
                'packet_loss_mean': 0.1, 'packet_loss_std': 0.05
            },
            TrafficProfile.URLLC: {
                'latency_mean': 5.0, 'latency_std': 1.5,
                'throughput_mean': 200.0, 'throughput_std': 40.0,
                'packet_loss_mean': 0.01, 'packet_loss_std': 0.005
            },
            TrafficProfile.MMTC: {
                'latency_mean': 100.0, 'latency_std': 30.0,
                'throughput_mean': 50.0, 'throughput_std': 15.0,
                'packet_loss_mean': 0.5, 'packet_loss_std': 0.2
            },
            TrafficProfile.MIXED: {
                'latency_mean': 30.0, 'latency_std': 10.0,
                'throughput_mean': 500.0, 'throughput_std': 120.0,
                'packet_loss_mean': 0.2, 'packet_loss_std': 0.1
            }
        }
    
    def generate_baseline_kpi(self, cell_id: str, traffic_profile: TrafficProfile, timestamp: datetime) -> NetworkKPI:
        """Generate a baseline (normal) KPI measurement"""
        params = self.profile_params[traffic_profile]
        
        latency = max(0.1, np.random.normal(params['latency_mean'], params['latency_std']))
        throughput = max(1.0, np.random.normal(params['throughput_mean'], params['throughput_std']))
        packet_loss = np.clip(np.random.normal(params['packet_loss_mean'], params['packet_loss_std']), 0.0, 5.0)
        jitter = max(0.1, np.random.exponential(latency * 0.1))
        signal_strength = np.random.uniform(-90, -60)
        active_users = np.random.poisson(50)
        
        return NetworkKPI(
            timestamp=timestamp, cell_id=cell_id, traffic_profile=traffic_profile,
            latency_ms=round(latency, 2), throughput_mbps=round(throughput, 2),
            packet_loss_pct=round(packet_loss, 4), jitter_ms=round(jitter, 2),
            signal_strength_dbm=round(signal_strength, 1), active_users=active_users
        )
    
    def inject_latency_spike(self, kpi: NetworkKPI, spike_multiplier: float = 3.0) -> NetworkKPI:
        """Inject a latency spike anomaly"""
        kpi.latency_ms *= spike_multiplier
        if kpi.jitter_ms:
            kpi.jitter_ms *= spike_multiplier * 0.8
        return kpi
    
    def inject_throughput_drop(self, kpi: NetworkKPI, drop_factor: float = 0.4) -> NetworkKPI:
        """Inject a throughput drop anomaly"""
        kpi.throughput_mbps *= drop_factor
        kpi.packet_loss_pct = min(10.0, kpi.packet_loss_pct * 3.0)
        return kpi
    
    def inject_congestion_pattern(self, kpi: NetworkKPI) -> NetworkKPI:
        """Inject congestion pattern"""
        kpi.latency_ms *= 2.5
        kpi.throughput_mbps *= 0.5
        kpi.packet_loss_pct = min(8.0, kpi.packet_loss_pct * 4.0)
        if kpi.active_users:
            kpi.active_users = int(kpi.active_users * 1.8)
        return kpi
    
    def generate_kpi_stream(
        self, cell_ids: List[str], traffic_profiles: List[TrafficProfile],
        start_time: datetime, duration_hours: float = 1.0,
        interval_seconds: int = 10, anomaly_rate: float = 0.05
    ) -> List[NetworkKPI]:
        """Generate a stream of KPI measurements with injected anomalies"""
        kpis = []
        num_measurements = int((duration_hours * 3600) / interval_seconds)
        
        for i in range(num_measurements):
            timestamp = start_time + timedelta(seconds=i * interval_seconds)
            
            for cell_id in cell_ids:
                for traffic_profile in traffic_profiles:
                    kpi = self.generate_baseline_kpi(cell_id, traffic_profile, timestamp)
                    
                    if random.random() < anomaly_rate:
                        anomaly_type = random.choice(['latency_spike', 'throughput_drop', 'congestion'])
                        
                        if anomaly_type == 'latency_spike':
                            kpi = self.inject_latency_spike(kpi, spike_multiplier=random.uniform(2.5, 5.0))
                        elif anomaly_type == 'throughput_drop':
                            kpi = self.inject_throughput_drop(kpi, drop_factor=random.uniform(0.3, 0.6))
                        elif anomaly_type == 'congestion':
                            kpi = self.inject_congestion_pattern(kpi)
                    
                    kpis.append(kpi)
        
        return kpis