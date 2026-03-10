/**
 * Format player count range for display
 *
 * @param min - Minimum players
 * @param max - Maximum players
 * @returns Formatted string (e.g., "2-4 players", "5+ players", "Solo")
 */
export function formatPlayerCount(min: number | null, max: number | null): string {
  if (min === null && max === null) return 'Unknown';
  if (min === null) return `Up to ${max} players`;
  if (max === null) return `${min}+ players`;

  if (min === max) {
    return min === 1 ? 'Solo' : `${min} players`;
  }

  return `${min}-${max} players`;
}

/**
 * Format complexity/weight for display
 *
 * @param complexity - Complexity value (1-5 scale)
 * @returns Human-readable label (e.g., "Light", "Medium", "Heavy")
 */
export function formatComplexity(complexity: number | null): string {
  if (complexity === null) return 'Unknown';

  if (complexity < 2) return 'Light';
  if (complexity < 3) return 'Medium-Light';
  if (complexity < 4) return 'Medium';
  if (complexity < 4.5) return 'Medium-Heavy';
  return 'Heavy';
}

/**
 * Format playing time for display
 *
 * @param minutes - Playing time in minutes
 * @returns Formatted string (e.g., "30 min", "2 hr", "2 hr 30 min")
 */
export function formatPlayingTime(minutes: number | null): string {
  if (minutes === null) return 'Unknown';
  if (minutes < 60) return `${minutes} min`;

  const hours = Math.floor(minutes / 60);
  const remainingMinutes = minutes % 60;

  if (remainingMinutes === 0) {
    return `${hours} hr`;
  }

  return `${hours} hr ${remainingMinutes} min`;
}

/**
 * Format rating for display
 *
 * @param rating - Rating value (0-10 scale)
 * @returns Formatted string (e.g., "7.8/10")
 */
export function formatRating(rating: number | null): string {
  if (rating === null) return 'Not rated';
  return `${rating.toFixed(1)}/10`;
}

/**
 * Truncate long text with ellipsis
 *
 * @param text - Text to truncate
 * @param maxLength - Maximum length before truncation
 * @returns Truncated text
 */
export function truncateText(text: string, maxLength: number): string {
  if (text.length <= maxLength) return text;
  return text.substring(0, maxLength).trim() + '...';
}

/**
 * Format score as percentage
 *
 * @param score - Score value (0-1 scale)
 * @returns Formatted percentage (e.g., "78%")
 */
export function formatScore(score: number): string {
  return `${Math.round(score * 100)}%`;
}
