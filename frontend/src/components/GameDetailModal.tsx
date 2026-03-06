import {
  Modal,
  ModalOverlay,
  ModalContent,
  ModalHeader,
  ModalBody,
  ModalCloseButton,
  ModalFooter,
  Button,
  Image,
  Text,
  VStack,
  HStack,
  Badge,
  Progress,
  SimpleGrid,
  Box,
  Link,
  Wrap,
  WrapItem,
  Divider,
} from '@chakra-ui/react';
import { ExternalLinkIcon } from '@chakra-ui/icons';
import type { GameRecommendation } from '../types/api';
import {
  formatPlayerCount,
  formatComplexity,
  formatPlayingTime,
  formatRating,
  formatScore,
} from '../utils/formatting';

interface GameDetailModalProps {
  game: GameRecommendation;
  isOpen: boolean;
  onClose: () => void;
  isSelected: boolean;
  onToggleSelection: (gameId: number) => void;
}

/**
 * Full game details modal
 *
 * Shows:
 * - Full-size image
 * - Complete description
 * - Full explanation (why recommended)
 * - Metadata: mechanics, categories, complexity, rating, players, time, age
 * - Score visualization (progress bar)
 * - Link to BoardGameGeek
 * - "Add to Comparison" button
 */
export default function GameDetailModal({
  game,
  isOpen,
  onClose,
  isSelected,
  onToggleSelection,
}: GameDetailModalProps) {
  const bggUrl = `https://boardgamegeek.com/boardgame/${game.id}`;

  return (
    <Modal isOpen={isOpen} onClose={onClose} size="xl" scrollBehavior="inside">
      <ModalOverlay />
      <ModalContent>
        <ModalHeader>
          {game.name}
          {game.year_published && (
            <Text as="span" fontSize="md" color="gray.600" ml={2}>
              ({game.year_published})
            </Text>
          )}
        </ModalHeader>
        <ModalCloseButton />

        <ModalBody>
          <VStack spacing={4} align="stretch">
            {/* Full Image */}
            <Image
              src={game.image_url || game.thumbnail_url || 'https://via.placeholder.com/400x400?text=No+Image'}
              alt={game.name}
              borderRadius="md"
              maxH="400px"
              objectFit="contain"
              fallbackSrc="https://via.placeholder.com/400x400?text=No+Image"
            />

            {/* Recommendation Score */}
            <Box>
              <HStack justify="space-between" mb={2}>
                <Text fontWeight="bold">Recommendation Score</Text>
                <Badge colorScheme="green" fontSize="lg">
                  {formatScore(game.score)}
                </Badge>
              </HStack>
              <Progress value={game.score * 100} colorScheme="green" size="lg" borderRadius="md" />
            </Box>

            {/* Explanation */}
            <Box>
              <Text fontWeight="bold" mb={2}>
                Why this game?
              </Text>
              <Text color="gray.700">{game.explanation}</Text>
            </Box>

            <Divider />

            {/* Key Stats Grid */}
            <SimpleGrid columns={2} spacing={4}>
              <Box>
                <Text fontSize="sm" color="gray.600">
                  Players
                </Text>
                <Text fontWeight="medium">{formatPlayerCount(game.min_players, game.max_players)}</Text>
              </Box>

              <Box>
                <Text fontSize="sm" color="gray.600">
                  Playing Time
                </Text>
                <Text fontWeight="medium">{formatPlayingTime(game.playing_time)}</Text>
              </Box>

              <Box>
                <Text fontSize="sm" color="gray.600">
                  Complexity
                </Text>
                <Text fontWeight="medium">
                  {formatComplexity(game.complexity)}
                  {game.complexity !== null && ` (${game.complexity.toFixed(1)})`}
                </Text>
              </Box>

              <Box>
                <Text fontSize="sm" color="gray.600">
                  Rating
                </Text>
                <Text fontWeight="medium">{formatRating(game.rating)}</Text>
              </Box>

              {game.min_age !== null && (
                <Box>
                  <Text fontSize="sm" color="gray.600">
                    Minimum Age
                  </Text>
                  <Text fontWeight="medium">{game.min_age}+</Text>
                </Box>
              )}
            </SimpleGrid>

            <Divider />

            {/* Mechanics */}
            {game.mechanics.length > 0 && (
              <Box>
                <Text fontWeight="bold" mb={2}>
                  Mechanics
                </Text>
                <Wrap spacing={2}>
                  {game.mechanics.map(mechanic => (
                    <WrapItem key={mechanic}>
                      <Badge colorScheme="blue">{mechanic}</Badge>
                    </WrapItem>
                  ))}
                </Wrap>
              </Box>
            )}

            {/* Categories */}
            {game.categories.length > 0 && (
              <Box>
                <Text fontWeight="bold" mb={2}>
                  Categories
                </Text>
                <Wrap spacing={2}>
                  {game.categories.map(category => (
                    <WrapItem key={category}>
                      <Badge colorScheme="purple">{category}</Badge>
                    </WrapItem>
                  ))}
                </Wrap>
              </Box>
            )}

            <Divider />

            {/* Description */}
            <Box>
              <Text fontWeight="bold" mb={2}>
                Description
              </Text>
              <Text fontSize="sm" color="gray.700">
                {game.description}
              </Text>
            </Box>

            {/* BGG Link */}
            <Link href={bggUrl} isExternal color="blue.500">
              View on BoardGameGeek <ExternalLinkIcon mx="2px" />
            </Link>
          </VStack>
        </ModalBody>

        <ModalFooter>
          <Button
            colorScheme={isSelected ? 'red' : 'blue'}
            onClick={() => onToggleSelection(game.id)}
            mr={3}
          >
            {isSelected ? 'Remove from Comparison' : 'Add to Comparison'}
          </Button>
          <Button variant="ghost" onClick={onClose}>
            Close
          </Button>
        </ModalFooter>
      </ModalContent>
    </Modal>
  );
}
