import { useState } from 'react';
import {
  Card,
  CardBody,
  Image,
  Stack,
  Heading,
  Text,
  Badge,
  HStack,
  Checkbox,
  Box,
} from '@chakra-ui/react';
import type { GameRecommendation } from '../types/api';
import { formatScore, truncateText } from '../utils/formatting';
import GameDetailModal from './GameDetailModal';

interface GameCardProps {
  game: GameRecommendation;
  isSelected: boolean;
  onToggleSelection: (gameId: number) => void;
}

/**
 * Individual game card showing thumbnail, name, score, and brief explanation
 *
 * Features:
 * - Thumbnail image (or placeholder if missing)
 * - Game name and year
 * - Score badge (0-100%)
 * - Truncated explanation (2 lines preview)
 * - Checkbox to add to comparison
 * - Click to open detail modal
 */
export default function GameCard({ game, isSelected, onToggleSelection }: GameCardProps) {
  const [isModalOpen, setIsModalOpen] = useState(false);

  const handleCardClick = () => {
    setIsModalOpen(true);
  };

  const handleCheckboxClick = (e: React.MouseEvent) => {
    e.stopPropagation(); // Prevent modal from opening
    onToggleSelection(game.id);
  };

  return (
    <>
      <Card
        cursor="pointer"
        onClick={handleCardClick}
        _hover={{ transform: 'translateY(-4px)', shadow: 'lg' }}
        transition="all 0.2s"
        border={isSelected ? '2px' : '1px'}
        borderColor={isSelected ? 'blue.500' : 'gray.200'}
      >
        <CardBody>
          <Stack spacing={3}>
            {/* Thumbnail */}
            <Image
              src={game.thumbnail_url || 'https://via.placeholder.com/200x200?text=No+Image'}
              alt={game.name}
              borderRadius="md"
              objectFit="cover"
              height="200px"
              fallbackSrc="https://via.placeholder.com/200x200?text=No+Image"
            />

            {/* Game Name and Year */}
            <Box>
              <Heading size="md" noOfLines={2}>
                {game.name}
              </Heading>
              {game.year_published && (
                <Text fontSize="sm" color="gray.600">
                  {game.year_published}
                </Text>
              )}
            </Box>

            {/* Score Badge */}
            <HStack>
              <Badge colorScheme="green" fontSize="md" px={2} py={1}>
                {formatScore(game.score)} Match
              </Badge>
              {game.rating && (
                <Badge colorScheme="yellow" fontSize="sm">
                  ⭐ {game.rating.toFixed(1)}
                </Badge>
              )}
            </HStack>

            {/* Brief Explanation */}
            <Text fontSize="sm" color="gray.700" noOfLines={2}>
              {truncateText(game.explanation, 120)}
            </Text>

            {/* Comparison Checkbox */}
            <Box onClick={handleCheckboxClick}>
              <Checkbox isChecked={isSelected} size="sm">
                Compare
              </Checkbox>
            </Box>
          </Stack>
        </CardBody>
      </Card>

      {/* Detail Modal */}
      <GameDetailModal
        game={game}
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        isSelected={isSelected}
        onToggleSelection={onToggleSelection}
      />
    </>
  );
}
