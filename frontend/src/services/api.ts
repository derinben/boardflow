import axios from 'axios';
import type { RecommendationRequest, RecommendationResponse, HealthCheckResponse } from '../types/api';

// API base URL - uses Vite proxy in dev, relative path in production
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api';

// Create axios instance with default config
const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 30000, // 30 seconds (LLM calls can be slow)
});

/**
 * Fetch game recommendations based on natural language query
 *
 * @param query - User's natural language query (e.g., "I like Catan, want something with trading")
 * @param topN - Number of recommendations to return (default 10)
 * @param yearMin - Minimum publication year filter (default 2015)
 * @returns Promise with recommendations array
 *
 * Example:
 *   const response = await getRecommendations("Games for 6+ players", 10, 2015);
 *   console.log(response.recommendations); // Array of GameRecommendation objects
 */
export async function getRecommendations(
  query: string,
  topN: number = 10,
  yearMin: number = 2015
): Promise<RecommendationResponse> {
  const request: RecommendationRequest = {
    query,
    top_n: topN,
    year_min: yearMin,
  };

  const response = await apiClient.post<RecommendationResponse>('/recommendations', request);
  return response.data;
}

/**
 * Health check endpoint to verify backend connectivity
 *
 * @returns Promise with health status
 */
export async function checkHealth(): Promise<HealthCheckResponse> {
  const response = await apiClient.get<HealthCheckResponse>('/health');
  return response.data;
}
