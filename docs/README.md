# 📚 Documentation — AI Sports Injury Risk Detection

This directory contains all project documentation including architecture diagrams, API references, setup guides, and deployment instructions.

## 📁 Folder Structure (Planned)

```
docs/
├── architecture/               # System architecture diagrams & explanations
│   ├── system-overview.md
│   ├── ml-pipeline.md
│   └── data-flow.md
├── api/                        # API endpoint documentation
│   ├── auth-api.md
│   ├── athlete-api.md
│   ├── video-api.md
│   └── reports-api.md
├── deployment/                 # Deployment and DevOps guides
│   ├── docker-setup.md
│   ├── aws-deployment.md
│   └── environment-setup.md
├── guides/                     # Developer and user guides
│   ├── getting-started.md
│   ├── contributing.md
│   └── user-manual.md
└── README.md
```

## 📖 Documentation Index

### 🏗️ Architecture
| Document | Description |
|----------|-------------|
| `system-overview.md` | High-level system architecture |
| `ml-pipeline.md` | AI/ML data processing pipeline |
| `data-flow.md` | Data flow from video input to risk score |

### 🔗 API Reference
| Document | Description |
|----------|-------------|
| `auth-api.md` | Authentication endpoints (login, register, refresh) |
| `athlete-api.md` | Athlete profile CRUD operations |
| `video-api.md` | Video upload and analysis endpoints |
| `reports-api.md` | Report generation and export endpoints |

### 🚀 Deployment
| Document | Description |
|----------|-------------|
| `docker-setup.md` | Docker and Docker Compose setup |
| `aws-deployment.md` | Deploying to AWS (EC2, S3, RDS) |
| `environment-setup.md` | Environment variable configuration |

### 📘 Guides
| Document | Description |
|----------|-------------|
| `getting-started.md` | Full local development setup guide |
| `contributing.md` | How to contribute — branch, PR, code review rules |
| `user-manual.md` | End-user guide for all roles |

## 🏗️ System Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                        CLIENT LAYER                         │
│              React.js / Next.js Frontend                    │
└─────────────────────────┬───────────────────────────────────┘
                          │ HTTPS / REST API
┌─────────────────────────▼───────────────────────────────────┐
│                       API LAYER                             │
│                FastAPI (Python) Backend                     │
│         Auth │ Athletes │ Videos │ Reports │ Alerts         │
└──────┬────────────────────────────────────────┬─────────────┘
       │                                        │
┌──────▼──────────┐                  ┌──────────▼──────────────┐
│   DATA LAYER    │                  │      AI/ML LAYER        │
│  PostgreSQL     │                  │  Pose Estimation        │
│  MongoDB        │                  │  Biomechanical Analysis │
└─────────────────┘                  │  Injury Prediction      │
                                     │  Risk Scoring           │
                                     │  Recommendations        │
                                     └─────────────────────────┘
```

## 🤝 Contributing

Please read `guides/contributing.md` before raising a Pull Request.

### Branch Naming Convention
```
feature/<module-name>      # New features
bugfix/<issue-description> # Bug fixes
hotfix/<critical-fix>      # Critical production fixes
docs/<document-name>       # Documentation updates
```

### Commit Message Convention
```
🎉  Initial commit / new feature
✨  New feature added
🐛  Bug fix
📝  Documentation update
♻️  Refactor
🔧  Config / setup changes
✅  Tests added or fixed
🚀  Deployment related
```

## 📞 Contact & Support

For questions about the project, raise a GitHub Issue or contact the project maintainer.
