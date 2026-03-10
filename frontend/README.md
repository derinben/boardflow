# BoardFlow Frontend

React + TypeScript web interface for discovering board games through natural language search.

## Quick Start

```bash
# Install
npm install

# Development (requires backend on port 8000)
npm run dev

# Build for production
npm run build
```

## What You Need

- Node.js 20.19+ (20.10 works with warnings)
- Backend API running on http://localhost:8000

## Development Workflow

**Two terminals:**

```bash
# Terminal 1 - Backend
cd /path/to/boardflow
uvicorn api.main:app --reload

# Terminal 2 - Frontend
cd frontend
npm run dev
```

Open http://localhost:5173

## Architecture

- `types/api.ts` - TypeScript interfaces (match backend)
- `services/api.ts` - HTTP client (Axios)
- `hooks/useRecommendations.ts` - Search state
- `utils/` - Filters, formatting helpers
- `components/` - React UI components
- `App.tsx` - Main layout

## For Beginners

See **FRONTEND_GUIDE.md** for:
- How React works
- Component structure explained
- State flow diagrams
- Debugging tips

## Tech Stack

- React 19 + TypeScript + Vite 7
- Chakra UI v2 (accessible components)
- Axios (HTTP client)

## Troubleshooting

**Backend not connecting?**
1. Check backend is running: `curl http://localhost:8000/api/health`
2. Verify proxy in vite.config.ts
3. Check browser console (F12 → Network tab)

**Build errors?**
- Ensure Chakra UI v2.8.2: `npm list @chakra-ui/react`
- Clear and reinstall: `rm -rf node_modules && npm install`

## Production

Build creates `dist/` folder:
```bash
npm run build
```

Backend serves these static files in production.
