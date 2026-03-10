import type { GameRecommendation } from '../types/api';

export interface GameFilters {
  complexityRange: [number, number];  // [min, max] on 1-5 scale
  minPlayers: number | null;
  maxPlayers: number | null;
  selectedMechanics: string[];
  selectedCategories: string[];
}

export type SortOption = 'score' | 'rating' | 'complexity' | 'year';

/**
 * Apply client-side filters to game results
 *
 * @param games - Full results array from API
 * @param filters - Active filter criteria
 * @returns Filtered game array
 */
export function applyFilters(games: GameRecommendation[], filters: GameFilters): GameRecommendation[] {
  return games.filter(game => {
    // Complexity filter
    if (game.complexity !== null) {
      const [minComplexity, maxComplexity] = filters.complexityRange;
      if (game.complexity < minComplexity || game.complexity > maxComplexity) {
        return false;
      }
    }

    // Player count filter (game must support the specified range)
    if (filters.minPlayers !== null && game.max_players !== null) {
      if (game.max_players < filters.minPlayers) return false;
    }
    if (filters.maxPlayers !== null && game.min_players !== null) {
      if (game.min_players > filters.maxPlayers) return false;
    }

    // Mechanics filter (game must have ALL selected mechanics)
    if (filters.selectedMechanics.length > 0) {
      const hasAllMechanics = filters.selectedMechanics.every(mechanic =>
        game.mechanics.includes(mechanic)
      );
      if (!hasAllMechanics) return false;
    }

    // Categories filter (game must have ALL selected categories)
    if (filters.selectedCategories.length > 0) {
      const hasAllCategories = filters.selectedCategories.every(category =>
        game.categories.includes(category)
      );
      if (!hasAllCategories) return false;
    }

    return true;
  });
}

/**
 * Sort games by specified criterion
 *
 * @param games - Game array to sort
 * @param sortBy - Sort criterion
 * @returns Sorted game array (new array, original unchanged)
 */
export function sortGames(games: GameRecommendation[], sortBy: SortOption): GameRecommendation[] {
  const sorted = [...games];

  switch (sortBy) {
    case 'score':
      // Best Match - highest score first
      return sorted.sort((a, b) => b.score - a.score);

    case 'rating':
      // Highest Rated - highest rating first (nulls last)
      return sorted.sort((a, b) => {
        if (a.rating === null) return 1;
        if (b.rating === null) return -1;
        return b.rating - a.rating;
      });

    case 'complexity':
      // Lowest Complexity - simplest first (nulls last)
      return sorted.sort((a, b) => {
        if (a.complexity === null) return 1;
        if (b.complexity === null) return -1;
        return a.complexity - b.complexity;
      });

    case 'year':
      // Newest - most recent first (nulls last)
      return sorted.sort((a, b) => {
        if (a.year_published === null) return 1;
        if (b.year_published === null) return -1;
        return b.year_published - a.year_published;
      });

    default:
      return sorted;
  }
}

/**
 * Extract unique mechanics from game array for filter options
 *
 * @param games - Game array
 * @returns Sorted array of unique mechanic names
 */
export function extractUniqueMechanics(games: GameRecommendation[]): string[] {
  const mechanics = new Set<string>();
  games.forEach(game => {
    game.mechanics.forEach(mechanic => mechanics.add(mechanic));
  });
  return Array.from(mechanics).sort();
}

/**
 * Extract unique categories from game array for filter options
 *
 * @param games - Game array
 * @returns Sorted array of unique category names
 */
export function extractUniqueCategories(games: GameRecommendation[]): string[] {
  const categories = new Set<string>();
  games.forEach(game => {
    game.categories.forEach(category => categories.add(category));
  });
  return Array.from(categories).sort();
}
