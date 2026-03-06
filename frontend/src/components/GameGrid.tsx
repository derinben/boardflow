import { SimpleGrid } from '@chakra-ui/react';
import type { GameRecommendation } from '../types/api';
import GameCard from './GameCard';

interface GameGridProps {
  games: GameRecommendation[];
  selectedGames: number[];
  onToggleSelection: (gameId: number) => void;
}

/**
 * Responsive grid layout for game cards
 *
 * Breakpoints:
 * - Mobile (< 768px): 1 column
 * - Tablet (768-1024px): 2 columns
 * - Desktop (> 1024px): 3-4 columns
 */
export default function GameGrid({ games, selectedGames, onToggleSelection }: GameGridProps) {
  return (
    <SimpleGrid columns={{ base: 1, md: 2, lg: 3, xl: 4 }} spacing={4}>
      {games.map(game => (
        <GameCard
          key={game.id}
          game={game}
          isSelected={selectedGames.includes(game.id)}
          onToggleSelection={onToggleSelection}
        />
      ))}
    </SimpleGrid>
  );
}
