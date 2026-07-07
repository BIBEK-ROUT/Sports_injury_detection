# 🏃 AI Sports Injury Risk Detection from Video

An AI-powered platform that analyzes athlete movement videos to detect biomechanical issues, predict injury risks, and provide corrective recommendations.

## 🎯 Project Overview

This platform leverages **Computer Vision**, **Pose Estimation**, **Biomechanics Analysis**, and **Predictive Analytics** to help athletes, coaches, physiotherapists, and sports scientists proactively prevent injuries.

## 🛠️ Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React.js, Next.js, Tailwind CSS |
| Backend | Python, FastAPI |
| Database | PostgreSQL, MongoDB |
| AI/CV | OpenCV, YOLOv8, MediaPipe, TensorFlow, PyTorch |
| ML | XGBoost, Scikit-learn, Pandas, NumPy |
| Pose | OpenPose, MediaPipe Pose, MoveNet, Detectron2 |
| Video | OpenCV, FFmpeg, DeepSORT |
| DevOps | Docker, AWS/Azure, GitHub Actions |

## 📁 Project Structure

```
Sports_Injury_detection/
├── backend/                  # FastAPI Backend
│   ├── app/
│   │   ├── api/routes/       # API endpoints
│   │   ├── core/             # Config, security, database
│   │   ├── models/           # Database models
│   │   ├── schemas/          # Pydantic schemas
│   │   ├── services/         # Business logic
│   │   ├── ml/               # AI/ML modules
│   │   │   ├── pose_estimation/
│   │   │   ├── biomechanics/
│   │   │   ├── injury_prediction/
│   │   │   ├── anomaly_detection/
│   │   │   ├── risk_scoring/
│   │   │   └── recommendations/
│   │   ├── video/            # Video processing
│   │   └── utils/
│   ├── tests/
│   └── alembic/              # DB migrations
├── frontend/                 # React/Next.js Frontend
│   ├── src/
│   │   ├── components/
│   │   │   ├── common/
│   │   │   ├── dashboard/
│   │   │   ├── athlete/
│   │   │   ├── video/
│   │   │   └── reports/
│   │   ├── pages/
│   │   ├── hooks/
│   │   ├── store/
│   │   ├── services/
│   │   ├── styles/
│   │   └── utils/
│   └── public/
├── docker/                   # Docker configs
├── docs/                     # Documentation
│   ├── architecture/
│   ├── api/
│   └── deployment/
├── datasets/                 # Dataset references
├── notebooks/                # Jupyter notebooks
├── scripts/                  # Utility scripts
├── docker-compose.yml
└── README.md
```

## 🚀 Modules

1. **User Authentication & RBAC** — JWT, OAuth2, Role-based access
2. **Athlete Profile Management** — Registration, injury history, training profiles
3. **Video Upload & Processing** — Upload, preprocessing, frame extraction
4. **Pose Estimation Engine** — Joint tracking, skeleton generation
5. **Biomechanical Analysis** — Joint angles, symmetry, posture
6. **Injury Risk Prediction** — ACL, Hamstring, Ankle, Shoulder risk detection
7. **Movement Anomaly Detection** — Deviation & fatigue monitoring
8. **Risk Scoring Engine** — Weighted risk scoring model
9. **Corrective Recommendations** — Exercise & recovery suggestions
10. **Dashboards & Analytics** — Athlete, Coach, Physio, Admin dashboards
11. **Notification & Alert System** — Real-time risk alerts
12. **Reports & Export** — PDF, Excel exports
13. **Deployment** — Docker, Cloud, CI/CD

## 📅 Timeline (8 Weeks)

| Milestone | Week | Focus |
|-----------|------|-------|
| M1 | Week 1-2 | Setup, Auth, Profiles, Dataset Collection |
| M2 | Week 3-4 | Pose Estimation & Biomechanical Analysis |
| M3 | Week 5-6 | Injury Prediction & Recommendations |
| M4 | Week 7-8 | Dashboards, Testing & Deployment |

## 🌿 Branch Strategy

| Branch | Purpose |
|--------|---------|
| `main` | Production-ready code |
| `develop` | Integration branch |
| `feature/auth` | Authentication module |
| `feature/athlete-profile` | Athlete profile management |
| `feature/video-processing` | Video upload & processing |
| `feature/pose-estimation` | Pose estimation engine |
| `feature/biomechanics` | Biomechanical analysis |
| `feature/injury-prediction` | Injury risk prediction |
| `feature/risk-scoring` | Risk scoring engine |
| `feature/recommendations` | Corrective recommendations |
| `feature/dashboards` | All dashboards |
| `feature/notifications` | Notification system |
| `feature/reports` | Reports & exports |
| `feature/deployment` | Docker & cloud deployment |

## 🏁 Getting Started

```bash
# Clone the repository
git clone <repo-url>
cd Sports_Injury_detection

# Backend setup
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt

# Frontend setup
cd ../frontend
npm install
npm run dev
```

## 👥 Roles

- **Athlete** — View personal risk scores and recommendations
- **Coach** — Monitor team performance and risks
- **Physiotherapist** — Track rehabilitation and injury monitoring
- **Sports Scientist** — Biomechanical analytics and research
- **Administrator** — Platform management
