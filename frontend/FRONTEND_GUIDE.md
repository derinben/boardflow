# Frontend Beginner's Guide

## Overview

This React frontend displays boardgame recommendations from our FastAPI backend. When users type a query like "I like Catan", the app sends it to the API and shows matching games with scores and explanations.

## How It Works

**Flow**: User types query → Click search → API call → Display results → Click game for details

**Key Concepts**:
- **Components**: Reusable UI pieces (like LEGO blocks). Each `.tsx` file is a component.
- **State**: Data that changes (query text, results, loading status). When state changes, UI re-renders.
- **Props**: Data passed from parent to child component (like function parameters).
- **Hooks**: React functions that manage state/side effects (useState, useEffect).

## File Structure

```
frontend/
├── src/
│   ├── main.tsx              # Entry point - loads App
│   ├── App.tsx               # Main page layout
│   ├── types/api.ts          # TypeScript interfaces (data shapes)
│   ├── services/api.ts       # HTTP calls to backend
│   ├── hooks/                # Custom state management
│   ├── components/           # UI pieces
│   └── utils/                # Helper functions
├── vite.config.ts            # Dev server config (proxy to backend)
└── package.json              # Dependencies list
```

## Key Files Explained

### 1. `main.tsx` - Application Entry
Loads the App component into `<div id="root">` in `index.html`. Wraps with Chakra UI theme provider.

### 2. `App.tsx` - Main Layout
Container for all components. Manages global state (query, results, selected games). Renders:
- QueryInput → ExampleQueries → ResultsHeader → FilterBar → GameGrid → ComparisonBar

### 3. `types/api.ts` - Data Shapes
TypeScript interfaces matching backend schemas. Defines what data looks like:
```typescript
interface GameRecommendation {
  id: number;
  name: string;
  score: number;
  // ... etc
}
```

### 4. `services/api.ts` - Backend Communication
Axios client that calls POST `/api/recommendations`. Returns promise with results.

### 5. `hooks/useRecommendations.ts` - State Logic
Custom hook managing:
- `query` - Current search text
- `loading` - Is API call in progress?
- `error` - Did something fail?
- `results` - Game array from API
- `fetchRecommendations()` - Function to trigger search

## Component Hierarchy

```
App (manages query, results, selected games)
├── QueryInput (text input, submit button)
├── ExampleQueries (clickable chips)
├── FilterBar (complexity slider, player count)
├── ResultsHeader (count, sort dropdown)
├── GameGrid (responsive grid)
│   └── GameCard (for each game)
│       └── Opens GameDetailModal on click
└── ComparisonBar (selected games, compare button)
    └── Opens ComparisonModal
```

## State Flow

**Search Flow**:
1. User types in QueryInput → Updates `query` state in App
2. User clicks Submit → Calls `fetchRecommendations()`
3. Hook sets `loading=true`, calls `api.getRecommendations()`
4. API returns → Hook sets `results`, `loading=false`
5. Results update → GameGrid re-renders with new data

**Filter Flow**:
1. User moves complexity slider → Updates `filters` state
2. App calls `applyFilters(results, filters)` → Returns filtered array
3. GameGrid receives filtered array → Re-renders with subset

## Styling with Chakra UI

Chakra provides pre-built components with props for styling:

```tsx
<Box bg="gray.100" p={4} borderRadius="md">  {/* padding, background, rounded corners */}
  <Text fontSize="lg" fontWeight="bold">Hello</Text>
</Box>
```

Common components:
- `Box` - Generic container (like `<div>`)
- `Flex` - Flexbox layout
- `Grid, SimpleGrid` - Grid layouts
- `Button, Input, Select` - Form elements
- `Card, CardHeader, CardBody` - Content cards
- `Modal, ModalOverlay, ModalContent` - Dialogs

## Running the Frontend

**Development** (with backend):
```bash
# Terminal 1 - Backend
cd .
uvicorn api.main:app --reload

# Terminal 2 - Frontend
cd frontend
npm run dev
```
Open http://localhost:5173

**Production Build**:
```bash
cd frontend
npm run build  # Creates frontend/dist/
```
Backend serves files from `/dist` in production.

## Common Patterns

### Making API Call
```tsx
const { data, loading, error } = useRecommendations();

if (loading) return <Spinner />;
if (error) return <Alert>Error: {error}</Alert>;
return <div>{data.map(game => <GameCard game={game} />)}</div>;
```

### Passing Data Down
```tsx
// Parent
<GameCard game={gameData} onClick={handleClick} />

// Child
function GameCard({ game, onClick }) {
  return <Card onClick={() => onClick(game.id)}>{game.name}</Card>;
}
```

### Managing State
```tsx
const [query, setQuery] = useState('');  // Initialize empty string
setQuery('New value');  // Update triggers re-render
```

## Debugging Tips

1. **Console Logs**: Add `console.log(results)` to see data
2. **React DevTools**: Browser extension to inspect component state
3. **Network Tab**: See API calls/responses in browser DevTools
4. **TypeScript Errors**: Red squiggles = type mismatch, hover for details

## Next Steps

Read through components in this order:
1. `types/api.ts` - Understand data structure
2. `services/api.ts` - See how we call backend
3. `hooks/useRecommendations.ts` - State management
4. `App.tsx` - Main layout
5. `components/QueryInput.tsx` - Simplest component
6. `components/GameCard.tsx` - Display logic
7. `components/GameDetailModal.tsx` - Complex interactions
