# 🗄️ Database — AI Sports Injury Risk Detection

This directory contains all database-related files including schemas, migration scripts, seed data, and Entity-Relationship diagrams.

## 🛠️ Databases Used

| Database | Purpose |
|----------|---------|
| **PostgreSQL** | Primary relational database — users, athletes, sessions, risk scores |
| **MongoDB** | Secondary NoSQL database — video metadata, pose keypoints, analysis results |

## 📁 Folder Structure (Planned)

```
database/
├── postgres/
│   ├── schema.sql              # Full DB schema
│   ├── migrations/             # Alembic migration scripts
│   └── seeds/                  # Initial seed data
├── mongodb/
│   ├── collections.md          # Collection definitions
│   └── indexes.js              # MongoDB index setup
├── diagrams/
│   ├── erd.png                 # Entity Relationship Diagram
│   └── schema_overview.md      # Schema documentation
└── README.md
```

## 🗂️ PostgreSQL — Core Tables (Planned)

| Table | Description |
|-------|-------------|
| `users` | All users (athletes, coaches, physios, admins) |
| `roles` | Role definitions (Athlete, Coach, Physiotherapist, etc.) |
| `athlete_profiles` | Athlete details (sport, position, height, weight) |
| `injury_history` | Past injury records per athlete |
| `training_sessions` | Training load and session data |
| `video_uploads` | Uploaded video metadata |
| `analysis_results` | Pose estimation and biomechanical results |
| `risk_scores` | Injury risk scores per session |
| `recommendations` | Corrective exercise recommendations |
| `notifications` | System alerts and warnings |
| `reports` | Generated reports metadata |

## 📦 MongoDB — Core Collections (Planned)

| Collection | Description |
|------------|-------------|
| `pose_keypoints` | Raw pose keypoint data per video frame |
| `biomechanical_data` | Joint angles, symmetry, stride metrics |
| `movement_anomalies` | Detected movement deviations |
| `video_frames` | Extracted frame metadata |
| `audit_logs` | System activity logs |

## 🔑 Key Relationships

```
users ──────────── roles
  │
  └── athlete_profiles
          │
          ├── injury_history
          ├── training_sessions
          └── video_uploads
                  │
                  ├── analysis_results ──── pose_keypoints (MongoDB)
                  ├── risk_scores
                  └── recommendations
```

## 🚀 Setup Instructions

```bash
# PostgreSQL — Create database
psql -U postgres
CREATE DATABASE sports_injury_db;

# Run schema
psql -U postgres -d sports_injury_db -f postgres/schema.sql

# MongoDB — Start service
mongod --dbpath /data/db

# Create collections
mongosh sports_injury_db < mongodb/indexes.js
```

## 🌿 Development Branch

Database changes are tracked in: `database/` folder and managed via Alembic migrations in `backend/alembic/`.
