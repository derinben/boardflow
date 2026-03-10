import { Flex, Text, Select } from '@chakra-ui/react';
import type { SortOption } from '../utils/filters';

interface ResultsHeaderProps {
  totalCount: number;
  filteredCount: number;
  sortBy: SortOption;
  onSortChange: (sortBy: SortOption) => void;
}

/**
 * Header showing result count and sort controls
 *
 * Displays:
 * - "Showing X of Y games" (or just "Showing X games" if no filters active)
 * - Sort dropdown: Best Match, Highest Rated, Lowest Complexity, Newest
 */
export default function ResultsHeader({ totalCount, filteredCount, sortBy, onSortChange }: ResultsHeaderProps) {
  const hasFilters = filteredCount < totalCount;

  return (
    <Flex justify="space-between" align="center">
      <Text fontSize="lg" fontWeight="medium">
        {hasFilters ? `Showing ${filteredCount} of ${totalCount} games` : `Showing ${totalCount} games`}
      </Text>

      <Flex align="center" gap={2}>
        <Text fontSize="sm" color="gray.600">
          Sort by:
        </Text>
        <Select
          value={sortBy}
          onChange={(e) => onSortChange(e.target.value as SortOption)}
          width="200px"
          size="sm"
        >
          <option value="score">Best Match</option>
          <option value="rating">Highest Rated</option>
          <option value="complexity">Lowest Complexity</option>
          <option value="year">Newest</option>
        </Select>
      </Flex>
    </Flex>
  );
}
