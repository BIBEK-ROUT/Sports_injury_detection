# 🎨 Frontend — AI Sports Injury Risk Detection

This directory contains the complete frontend application built with **React.js** and **Next.js**.

## 🛠️ Tech Stack

| Tool | Purpose |
|------|---------|
| React.js | UI component library |
| Next.js | Framework (SSR, routing) |
| Tailwind CSS | Styling |
| Chart.js / Plotly | Data visualization |
| Axios | API communication |
| Redux Toolkit | State management |
| JWT | Auth token handling |

## 📁 Folder Structure (Planned)

```
frontend/
├── src/
│   ├── components/         # Reusable UI components
│   │   ├── common/         # Buttons, Inputs, Modals, Navbar
│   │   ├── dashboard/      # Dashboard cards and widgets
│   │   ├── athlete/        # Athlete profile components
│   │   ├── video/          # Video upload and player
│   │   └── reports/        # Report and chart components
│   ├── pages/              # Next.js pages / routes
│   ├── hooks/              # Custom React hooks
│   ├── store/              # Redux store and slices
│   ├── services/           # API service calls
│   ├── styles/             # Global CSS and theme
│   └── utils/              # Helper functions
├── public/                 # Static assets (images, icons)
├── package.json
├── next.config.js
└── tailwind.config.js
```

## 🖥️ Pages / Screens (Planned)

| Page | Route | Role |
|------|-------|------|
| Landing Page | `/` | Public |
| Login / Register | `/auth` | Public |
| Athlete Dashboard | `/dashboard/athlete` | Athlete |
| Coach Dashboard | `/dashboard/coach` | Coach |
| Physiotherapist Dashboard | `/dashboard/physio` | Physiotherapist |
| Sports Scientist Dashboard | `/dashboard/scientist` | Sports Scientist |
| Admin Dashboard | `/dashboard/admin` | Admin |
| Video Upload | `/video/upload` | Athlete, Coach |
| Video Analysis | `/video/analysis/:id` | All |
| Athlete Profile | `/athlete/:id` | All |
| Risk Reports | `/reports` | All |
| Notifications | `/notifications` | All |

## 🚀 Getting Started

```bash
# Navigate to frontend folder
cd frontend

# Install dependencies
npm install

# Run development server
npm run dev

# Build for production
npm run build
```

## 🌿 Development Branch

Active development happens on: `feature/dashboards`, `feature/auth`

> Merge into `develop` via Pull Request after review.
