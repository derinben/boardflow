import { useState, useCallback } from 'react';
import { getRecommendations } from '../services/api';
import type { GameRecommendation } from '../types/api';

interface UseRecommendationsResult {
  // State
  query: string;
  results: GameRecommendation[];
  loading: boolean;
  error: string | null;

  // Actions
  setQuery: (query: string) => void;
  fetchRecommendations: (topN?: number, yearMin?: number) => Promise<void>;
  clearResults: () => void;
}

/**
 * Custom hook for managing recommendation search state
 *
 * Handles:
 * - Query input state
 * - Loading/error states during API call
 * - Results storage
 * - Search trigger function
 *
 * Usage:
 *   const { query, setQuery, results, loading, error, fetchRecommendations } = useRecommendations();
 *
 *   <Input value={query} onChange={(e) => setQuery(e.target.value)} />
 *   <Button onClick={() => fetchRecommendations()}>Search</Button>
 *   {loading && <Spinner />}
 *   {results.map(game => <GameCard game={game} />)}
 */
export function useRecommendations(): UseRecommendationsResult {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<GameRecommendation[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchRecommendations = useCallback(
    async (topN: number = 10, yearMin: number = 2015) => {
      if (!query.trim()) {
        setError('Please enter a query');
        return;
      }

      if (query.length < 1 || query.length > 1000) {
        setError('Query must be between 1 and 1000 characters');
        return;
      }

      try {
        setLoading(true);
        setError(null);

        const response = await getRecommendations(query, topN, yearMin);
        setResults(response.recommendations);

        if (response.count === 0) {
          setError('No games found matching your query. Try different keywords.');
        }
      } catch (err) {
        console.error('Error fetching recommendations:', err);
        if (err instanceof Error) {
          setError(err.message);
        } else {
          setError('Failed to fetch recommendations. Please try again.');
        }
        setResults([]);
      } finally {
        setLoading(false);
      }
    },
    [query]
  );

  const clearResults = useCallback(() => {
    setResults([]);
    setError(null);
  }, []);

  return {
    query,
    results,
    loading,
    error,
    setQuery,
    fetchRecommendations,
    clearResults,
  };
}
