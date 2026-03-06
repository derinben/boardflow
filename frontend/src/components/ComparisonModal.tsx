import {
  Modal,
  ModalOverlay,
  ModalContent,
  ModalHeader,
  ModalBody,
  ModalCloseButton,
  Table,
  Thead,
  Tbody,
  Tr,
  Th,
  Td,
  Image,
  Badge,
  Wrap,
  WrapItem,
  Text,
  Box,
} from '@chakra-ui/react';
import type { GameRecommendation } from '../types/api';
import {
  formatPlayerCount,
  formatComplexity,
  formatPlayingTime,
  formatRating,
  formatScore,
} from '../utils/formatting';

interface ComparisonModalProps {
  games: GameRecommendation[];
  isOpen: boolean;
  onClose: () => void;
}

/**
 * Side-by-side comparison table for selected games
 *
 * Rows:
 * - Image
 * - Name
 * - Score
 * - Rating
 * - Complexity
 * - Players
 * - Playing Time
 * - Mechanics
 * - Categories
 * - Explanation
 */
export default function ComparisonModal({ games, isOpen, onClose }: ComparisonModalProps) {
  return (
    <Modal isOpen={isOpen} onClose={onClose} size="6xl" scrollBehavior="inside">
      <ModalOverlay />
      <ModalContent>
        <ModalHeader>Game Comparison</ModalHeader>
        <ModalCloseButton />

        <ModalBody>
          <Table variant="simple" size="sm">
            <Thead>
              <Tr>
                <Th width="150px">Property</Th>
                {games.map(game => (
                  <Th key={game.id}>{game.name}</Th>
                ))}
              </Tr>
            </Thead>

            <Tbody>
              {/* Images */}
              <Tr>
                <Td fontWeight="bold">Image</Td>
                {games.map(game => (
                  <Td key={game.id}>
                    <Image
                      src={game.thumbnail_url || 'https://via.placeholder.com/150x150?text=No+Image'}
                      alt={game.name}
                      boxSize="150px"
                      objectFit="cover"
                      borderRadius="md"
                      fallbackSrc="https://via.placeholder.com/150x150?text=No+Image"
                    />
                  </Td>
                ))}
              </Tr>

              {/* Year */}
              <Tr>
                <Td fontWeight="bold">Year</Td>
                {games.map(game => (
                  <Td key={game.id}>{game.year_published || 'Unknown'}</Td>
                ))}
              </Tr>

              {/* Score */}
              <Tr bg="green.50">
                <Td fontWeight="bold">Match Score</Td>
                {games.map(game => (
                  <Td key={game.id}>
                    <Badge colorScheme="green" fontSize="md">
                      {formatScore(game.score)}
                    </Badge>
                  </Td>
                ))}
              </Tr>

              {/* Rating */}
              <Tr>
                <Td fontWeight="bold">BGG Rating</Td>
                {games.map(game => (
                  <Td key={game.id}>{formatRating(game.rating)}</Td>
                ))}
              </Tr>

              {/* Complexity */}
              <Tr>
                <Td fontWeight="bold">Complexity</Td>
                {games.map(game => (
                  <Td key={game.id}>
                    {formatComplexity(game.complexity)}
                    {game.complexity !== null && ` (${game.complexity.toFixed(1)})`}
                  </Td>
                ))}
              </Tr>

              {/* Players */}
              <Tr>
                <Td fontWeight="bold">Players</Td>
                {games.map(game => (
                  <Td key={game.id}>{formatPlayerCount(game.min_players, game.max_players)}</Td>
                ))}
              </Tr>

              {/* Playing Time */}
              <Tr>
                <Td fontWeight="bold">Playing Time</Td>
                {games.map(game => (
                  <Td key={game.id}>{formatPlayingTime(game.playing_time)}</Td>
                ))}
              </Tr>

              {/* Min Age */}
              <Tr>
                <Td fontWeight="bold">Min Age</Td>
                {games.map(game => (
                  <Td key={game.id}>{game.min_age ? `${game.min_age}+` : 'Unknown'}</Td>
                ))}
              </Tr>

              {/* Mechanics */}
              <Tr>
                <Td fontWeight="bold" verticalAlign="top">
                  Mechanics
                </Td>
                {games.map(game => (
                  <Td key={game.id}>
                    <Wrap spacing={1}>
                      {game.mechanics.map(mechanic => (
                        <WrapItem key={mechanic}>
                          <Badge colorScheme="blue" fontSize="xs">
                            {mechanic}
                          </Badge>
                        </WrapItem>
                      ))}
                    </Wrap>
                  </Td>
                ))}
              </Tr>

              {/* Categories */}
              <Tr>
                <Td fontWeight="bold" verticalAlign="top">
                  Categories
                </Td>
                {games.map(game => (
                  <Td key={game.id}>
                    <Wrap spacing={1}>
                      {game.categories.map(category => (
                        <WrapItem key={category}>
                          <Badge colorScheme="purple" fontSize="xs">
                            {category}
                          </Badge>
                        </WrapItem>
                      ))}
                    </Wrap>
                  </Td>
                ))}
              </Tr>

              {/* Explanation */}
              <Tr bg="blue.50">
                <Td fontWeight="bold" verticalAlign="top">
                  Why Recommended
                </Td>
                {games.map(game => (
                  <Td key={game.id}>
                    <Box maxH="200px" overflowY="auto">
                      <Text fontSize="sm">{game.explanation}</Text>
                    </Box>
                  </Td>
                ))}
              </Tr>
            </Tbody>
          </Table>
        </ModalBody>
      </ModalContent>
    </Modal>
  );
}
