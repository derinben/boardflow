// TypeScript interfaces matching backend API schemas
// See: /home/derinroberts/fv/boardflow/api/schemas.py

export interface RecommendationRequest {
  query: string;          // Natural language query (1-1000 chars)
  top_n?: number;         // Number of recommendations (default 10, max 50)
  year_min?: number;      // Filter games published after this year (default 2015)
}

export interface GameRecommendation {
  // Core identifiers
  id: number;
  name: string;
  year_published: number | null;

  // Visual assets
  thumbnail_url: string | null;
  image_url: string | null;

  // Game description
  description: string;

  // Game properties
  mechanics: string[];          // e.g., ["Worker Placement", "Deck Building"]
  categories: string[];         // e.g., ["Card Game", "Fantasy"]
  complexity: number | null;    // 1-5 scale (average weight)
  rating: number | null;        // 0-10 Bayesian average

  // Player info
  min_players: number | null;
  max_players: number | null;
  playing_time: number | null;  // Minutes
  min_age: number | null;

  // Recommendation metadata
  score: number;                // 0-1 recommendation score
  explanation: string;          // Why this game was recommended
}

export interface RecommendationResponse {
  query: string;
  recommendations: GameRecommendation[];
  count: number;
}

export interface HealthCheckResponse {
  status: string;               // "healthy" or "degraded"
  database: string;             // "connected" or error message
  llm: string;                  // "configured" or "missing_api_key"
}
