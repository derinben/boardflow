import { useState } from 'react';
import {
  Box,
  Flex,
  Tag,
  TagLabel,
  TagCloseButton,
  Button,
  HStack,
} from '@chakra-ui/react';
import type { GameRecommendation } from '../types/api';
import ComparisonModal from './ComparisonModal';

interface ComparisonBarProps {
  selectedGames: GameRecommendation[];
  onRemoveGame: (gameId: number) => void;
  onClearAll: () => void;
}

/**
 * Fixed bottom bar showing selected games for comparison
 *
 * Features:
 * - Game name tags with remove button
 * - "Compare X games" button (disabled if < 2 selected)
 * - "Clear All" button
 * - Opens ComparisonModal on compare click
 *
 * Position: Fixed at bottom of page when games selected
 */
export default function ComparisonBar({ selectedGames, onRemoveGame, onClearAll }: ComparisonBarProps) {
  const [isComparisonOpen, setIsComparisonOpen] = useState(false);

  const canCompare = selectedGames.length >= 2;

  return (
    <>
      <Box
        position="fixed"
        bottom={0}
        left={0}
        right={0}
        bg="white"
        borderTop="2px"
        borderColor="gray.200"
        p={4}
        shadow="lg"
        zIndex={10}
      >
        <Flex justify="space-between" align="center" maxW="container.xl" mx="auto">
          <HStack spacing={2} flex={1} overflowX="auto">
            {selectedGames.map(game => (
              <Tag key={game.id} size="lg" colorScheme="blue" borderRadius="full">
                <TagLabel>{game.name}</TagLabel>
                <TagCloseButton onClick={() => onRemoveGame(game.id)} />
              </Tag>
            ))}
          </HStack>

          <HStack spacing={2} ml={4}>
            <Button size="sm" variant="ghost" onClick={onClearAll}>
              Clear All
            </Button>
            <Button
              colorScheme="blue"
              onClick={() => setIsComparisonOpen(true)}
              isDisabled={!canCompare}
            >
              Compare {selectedGames.length} Game{selectedGames.length !== 1 ? 's' : ''}
            </Button>
          </HStack>
        </Flex>
      </Box>

      {/* Comparison Modal */}
      <ComparisonModal
        games={selectedGames}
        isOpen={isComparisonOpen}
        onClose={() => setIsComparisonOpen(false)}
      />
    </>
  );
}
