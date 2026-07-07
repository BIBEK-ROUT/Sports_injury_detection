# ⚙️ Backend — AI Sports Injury Risk Detection

This directory contains the complete backend API and AI/ML engine built with **FastAPI** and **Python**.

## 🛠️ Tech Stack

| Tool | Purpose |
|------|---------|
| Python 3.11+ | Core language |
| FastAPI | REST API framework |
| Uvicorn | ASGI server |
| SQLAlchemy | ORM for PostgreSQL |
| PyMongo | MongoDB client |
| Alembic | Database migrations |
| JWT / OAuth2 | Authentication |
| OpenCV | Video processing |
| YOLOv8 | Object & pose detection |
| MediaPipe | Pose estimation |
| TensorFlow / PyTorch | Deep learning models |
| XGBoost / Scikit-learn | Injury risk prediction |
| FFmpeg | Video encoding/decoding |
| DeepSORT | Multi-object tracking |
| Pandas / NumPy | Data processing |
| Docker | Containerization |

## 📁 Folder Structure (Planned)

```
backend/
├── app/
│   ├── api/
│   │   └── routes/             # API route handlers
│   │       ├── auth.py
│   │       ├── athletes.py
│   │       ├── videos.py
│   │       ├── analysis.py
│   │       ├── reports.py
│   │       └── notifications.py
│   ├── core/
│   │   ├── config.py           # App settings
│   │   ├── security.py         # JWT, password hashing
│   │   └── database.py         # DB connection
│   ├── models/                 # SQLAlchemy DB models
│   ├── schemas/                # Pydantic request/response schemas
│   ├── services/               # Business logic layer
│   ├── ml/                     # AI & ML modules
│   │   ├── pose_estimation/    # MediaPipe, OpenPose, MoveNet
│   │   ├── biomechanics/       # Joint angle, symmetry analysis
│   │   ├── injury_prediction/  # Risk prediction models
│   │   ├── anomaly_detection/  # Movement anomaly detection
│   │   ├── risk_scoring/       # Weighted risk scoring
│   │   └── recommendations/    # Corrective exercise engine
│   ├── video/                  # Video upload & processing
│   └── utils/                  # Helper utilities
├── tests/                      # Unit and integration tests
├── alembic/                    # DB migration scripts
│   └── versions/
├── requirements.txt
├── requirements-dev.txt
├── .env.example
├── Dockerfile
└── main.py
```

## 🔗 Core API Endpoints (Planned)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/auth/register` | User registration |
| POST | `/api/auth/login` | User login |
| GET | `/api/athletes/` | List athletes |
| POST | `/api/athletes/` | Create athlete profile |
| POST | `/api/videos/upload` | Upload video |
| GET | `/api/videos/{id}/analysis` | Get analysis results |
| GET | `/api/reports/{athlete_id}` | Get injury risk report |
| GET | `/api/notifications/` | Get alerts |

## 🤖 AI/ML Pipeline

```
Video Input
    ↓
Frame Extraction (OpenCV / FFmpeg)
    ↓
Pose Estimation (MediaPipe / YOLOv8 / MoveNet)
    ↓
Biomechanical Analysis (Joint angles, symmetry)
    ↓
Injury Risk Prediction (XGBoost / PyTorch)
    ↓
Anomaly Detection
    ↓
Risk Score Calculation
    ↓
Corrective Recommendations
    ↓
Dashboard & Reports
```

## 🚀 Getting Started

```bash
# Navigate to backend folder
cd backend

# Create virtual environment
python -m venv venv

# Activate virtual environment (Windows)
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy environment variables
cp .env.example .env

# Run migrations
alembic upgrade head

# Start development server
uvicorn main:app --reload --port 8000
```

## 📄 API Documentation

Once running, visit:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## 🌿 Development Branch

Active development happens on: `feature/auth`, `feature/video-processing`, `feature/pose-estimation`, etc.

> Merge into `develop` via Pull Request after review.
