# 🤝 Contributing Guide — AI Sports Injury Risk Detection

Welcome to the team! This guide explains how to work together effectively on this project as part of the **Infosys Springboard Virtual Internship**.

---

## 👥 Team Collaboration Rules

- **Never push directly to `main` or `develop`** — always use Pull Requests
- **Always work on a feature branch** assigned to you
- **Get at least 1 team member review** before merging a PR
- **Mentor approval required** before merging into `milestone_X` branches
- **Sync your branch daily** with `develop` to avoid conflicts

---

## 🌿 Branch Strategy

```
main                        ← Production (Mentor merges here)
  └── develop               ← Team integration branch
        ├── milestone_1     ← Mentor reviews & approves
        ├── milestone_2
        ├── milestone_3
        ├── milestone_4
        └── feature/*       ← Your working branches
```

### Branch Naming Convention

```
feature/<your-name>/<module>        # Feature work
bugfix/<your-name>/<issue>          # Bug fixes
docs/<your-name>/<doc-name>         # Documentation
test/<your-name>/<test-name>        # Test additions
```

**Examples:**
```
feature/bibek/auth-login
feature/john/pose-estimation
bugfix/priya/video-upload-crash
docs/rahul/api-reference
```

---

## 🔄 Step-by-Step Workflow

### Starting New Work
```bash
# 1. Always start from develop
git checkout develop
git pull origin develop

# 2. Create your feature branch
git checkout -b feature/<your-name>/<module>

# 3. Work on your changes
# ... write code ...

# 4. Stage and commit
git add .
git commit -m "✨ Add login API endpoint"

# 5. Push your branch
git push origin feature/<your-name>/<module>

# 6. Open a Pull Request on GitHub → target: milestone_X or develop
```

### Keeping Your Branch Updated
```bash
# Pull latest develop into your branch daily
git checkout feature/your-name/your-module
git merge develop
# Resolve any conflicts, then continue
```

---

## 📝 Commit Message Convention

Use emojis to make the git log readable:

| Emoji | Type | Example |
|-------|------|---------|
| 🎉 | Initial setup | `🎉 Project setup` |
| ✨ | New feature | `✨ Add pose estimation module` |
| 🐛 | Bug fix | `🐛 Fix video upload timeout` |
| 📝 | Documentation | `📝 Update API docs` |
| ♻️ | Refactor | `♻️ Refactor auth service` |
| 🔧 | Config change | `🔧 Update environment variables` |
| ✅ | Tests | `✅ Add unit tests for risk scoring` |
| 🚀 | Deployment | `🚀 Add Dockerfile for backend` |
| 🎨 | UI/Style | `🎨 Update dashboard layout` |
| 🗄️ | Database | `🗄️ Add athlete_profiles migration` |

---

## 🔍 Pull Request Rules

### Before Opening a PR
- [ ] Code runs without errors
- [ ] You have tested your changes locally
- [ ] No merge conflicts with `develop`
- [ ] Code is clean (no debug `print()` or `console.log()`)
- [ ] Relevant README updated if needed

### PR Title Format
```
[MODULE] Brief description of change

Examples:
[AUTH] Add JWT token refresh endpoint
[POSE] Integrate MediaPipe pose estimation
[UI] Add athlete dashboard layout
```

### PR Target Branch
| Your work is for | Target branch |
|-----------------|--------------|
| Week 1-2 tasks | `milestone_1` |
| Week 3-4 tasks | `milestone_2` |
| Week 5-6 tasks | `milestone_3` |
| Week 7-8 tasks | `milestone_4` |

---

## 🗂️ Module Ownership (Assign to Team Members)

| Module | Branch | Assigned To |
|--------|--------|-------------|
| Authentication & RBAC | `feature/auth` | TBD |
| Athlete Profile | `feature/athlete-profile` | TBD |
| Video Processing | `feature/video-processing` | TBD |
| Pose Estimation | `feature/pose-estimation` | TBD |
| Biomechanics | `feature/biomechanics` | TBD |
| Injury Prediction | `feature/injury-prediction` | TBD |
| Risk Scoring | `feature/risk-scoring` | TBD |
| Recommendations | `feature/recommendations` | TBD |
| Dashboards | `feature/dashboards` | TBD |
| Notifications | `feature/notifications` | TBD |
| Reports | `feature/reports` | TBD |
| Deployment | `feature/deployment` | TBD |

> 📌 Update this table once team members are assigned.

---

## 🚫 Rules — What NOT to Do

- ❌ Never force push (`git push --force`) to shared branches
- ❌ Never commit `.env` files or API keys
- ❌ Never push directly to `main` or `develop`
- ❌ Never merge your own PR without a review
- ❌ Never commit large dataset files (>50MB)

---

## 📞 Communication

- Raise a **GitHub Issue** for bugs, questions, or feature requests
- Tag your mentor (`@mentor-username`) on PRs for milestone reviews
- Daily standups — update your progress in the team channel
