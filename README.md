# 5G Network Performance Analytics Platform

A production-ready real-time 5G network KPI monitoring system with ML-powered anomaly detection.

## 🌟 Features

- **Real-time KPI Ingestion**: FastAPI endpoints for network measurements
- **Multiple Anomaly Detection Algorithms**:
  - Z-score based detection
  - Rolling baseline analysis
  - Isolation Forest (ML)
  - Throughput drop detection
  - Traffic instability detection
- **Interactive Dashboard**: React-based real-time visualization
- **Dual Database Architecture**: PostgreSQL + InfluxDB
- **5G Traffic Profiles**: eMBB, URLLC, mMTC support
- **RESTful API**: Complete API with Swagger documentation

## 🏗️ Architecture

- **Backend**: FastAPI (Python 3.11)
- **Frontend**: React with Recharts
- **Databases**: PostgreSQL (alerts), InfluxDB (time-series)
- **ML/Analytics**: scikit-learn, pandas, numpy
- **Infrastructure**: Docker, Docker Compose

## 🚀 Quick Start

### Prerequisites
- Docker Desktop
- Python 3.11+
- Node.js 18+

### Installation

1. Clone the repository:
```bash
git clone https://github.com/YOUR_USERNAME/5g-network-analytics-platform.git
cd 5g-network-analytics-platform
```

2. Start services:
```bash
docker-compose up -d
```

3. Generate test data:
```bash
curl -X POST "http://localhost:8000/api/v1/generate/synthetic?cell_ids=gNB_001_Cell_1&traffic_profiles=eMBB&duration_hours=1&anomaly_rate=0.08"
```

4. Install frontend dependencies:
```bash
cd frontend
npm install
npm start
```

## 📊 Access Points

- **Dashboard**: http://localhost:3000
- **API Documentation**: http://localhost:8000/docs
- **InfluxDB UI**: http://localhost:8086 (admin/adminpassword)

## 🎯 Project Highlights

- ✨ **Multi-Algorithm Anomaly Detection**: Z-score, Rolling Baseline, Isolation Forest
- 📊 **Real-time Visualization**: Interactive dashboards with auto-refresh
- 🗄️ **Hybrid Database**: PostgreSQL for metadata, InfluxDB for time-series
- 🐳 **Containerized**: Full Docker Compose setup for easy deployment
- 📡 **5G-Specific**: Supports eMBB, URLLC, and mMTC traffic profiles
- 🎨 **Production-Ready**: Professional API with Swagger docs

## 🛠️ Tech Stack

**Backend:**
- Python 3.11, FastAPI, Pydantic
- pandas, numpy, scikit-learn
- SQLAlchemy, InfluxDB Client

**Frontend:**
- React 18, Recharts, Lucide React

**Infrastructure:**
- Docker & Docker Compose
- PostgreSQL 15
- InfluxDB 2.7

## 🔧 API Endpoints

- `POST /api/v1/kpis/ingest` - Ingest KPI measurements
- `POST /api/v1/kpis/query` - Query historical KPIs
- `GET /api/v1/analytics/summary` - Statistical summary
- `POST /api/v1/anomaly/detect` - Run anomaly detection
- `POST /api/v1/generate/synthetic` - Generate test data

## 🎯 Use Cases

1. **Performance Debugging**: Analyze network issues during incidents
2. **Capacity Planning**: Identify cells near capacity limits
3. **Proactive Monitoring**: Detect anomalies before they impact users
4. **SLA Monitoring**: Track compliance with service level agreements

## 📝 License

MIT License

## 👤 Author

suhaskosari - [GitHub](https://github.com/suhaskosari)

## 🙏 Acknowledgments

Built for analyzing 5G network performance with focus on anomaly detection and real-time monitoring.
