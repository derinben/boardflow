import {
  Box,
  Flex,
  Text,
  RangeSlider,
  RangeSliderTrack,
  RangeSliderFilledTrack,
  RangeSliderThumb,
  NumberInput,
  NumberInputField,
  Button,
  Select,
  VStack,
  HStack,
  Tag,
  TagLabel,
  TagCloseButton,
  Wrap,
  WrapItem,
} from '@chakra-ui/react';
import { useState } from 'react';
import type { GameFilters } from '../utils/filters';

interface FilterBarProps {
  filters: GameFilters;
  onFiltersChange: (filters: GameFilters) => void;
  availableMechanics: string[];
  availableCategories: string[];
}

/**
 * Collapsible filter panel for refining results
 *
 * Filters:
 * - Complexity range (1-5 slider)
 * - Player count (min/max inputs)
 * - Mechanics (multi-select)
 * - Categories (multi-select)
 *
 * All filters are client-side - instant results
 */
export default function FilterBar({
  filters,
  onFiltersChange,
  availableMechanics,
  availableCategories,
}: FilterBarProps) {
  const [selectedMechanic, setSelectedMechanic] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('');

  const handleComplexityChange = (value: number[]) => {
    onFiltersChange({
      ...filters,
      complexityRange: [value[0], value[1]],
    });
  };

  const handleMinPlayersChange = (value: string) => {
    onFiltersChange({
      ...filters,
      minPlayers: value === '' ? null : parseInt(value),
    });
  };

  const handleMaxPlayersChange = (value: string) => {
    onFiltersChange({
      ...filters,
      maxPlayers: value === '' ? null : parseInt(value),
    });
  };

  const handleAddMechanic = () => {
    if (selectedMechanic && !filters.selectedMechanics.includes(selectedMechanic)) {
      onFiltersChange({
        ...filters,
        selectedMechanics: [...filters.selectedMechanics, selectedMechanic],
      });
      setSelectedMechanic('');
    }
  };

  const handleRemoveMechanic = (mechanic: string) => {
    onFiltersChange({
      ...filters,
      selectedMechanics: filters.selectedMechanics.filter(m => m !== mechanic),
    });
  };

  const handleAddCategory = () => {
    if (selectedCategory && !filters.selectedCategories.includes(selectedCategory)) {
      onFiltersChange({
        ...filters,
        selectedCategories: [...filters.selectedCategories, selectedCategory],
      });
      setSelectedCategory('');
    }
  };

  const handleRemoveCategory = (category: string) => {
    onFiltersChange({
      ...filters,
      selectedCategories: filters.selectedCategories.filter(c => c !== category),
    });
  };

  const handleResetFilters = () => {
    onFiltersChange({
      complexityRange: [1, 5],
      minPlayers: null,
      maxPlayers: null,
      selectedMechanics: [],
      selectedCategories: [],
    });
    setSelectedMechanic('');
    setSelectedCategory('');
  };

  return (
    <Box bg="gray.50" p={4} borderRadius="md" border="1px" borderColor="gray.200">
      <VStack spacing={4} align="stretch">
        <Flex justify="space-between" align="center">
          <Text fontWeight="bold">Filters</Text>
          <Button size="sm" variant="ghost" onClick={handleResetFilters}>
            Reset All
          </Button>
        </Flex>

        {/* Complexity Range */}
        <Box>
          <Text fontSize="sm" mb={2}>
            Complexity: {filters.complexityRange[0]} - {filters.complexityRange[1]}
          </Text>
          <RangeSlider
            min={1}
            max={5}
            step={0.5}
            value={filters.complexityRange}
            onChange={handleComplexityChange}
          >
            <RangeSliderTrack>
              <RangeSliderFilledTrack />
            </RangeSliderTrack>
            <RangeSliderThumb index={0} />
            <RangeSliderThumb index={1} />
          </RangeSlider>
        </Box>

        {/* Player Count */}
        <Box>
          <Text fontSize="sm" mb={2}>
            Player Count
          </Text>
          <HStack>
            <NumberInput
              value={filters.minPlayers ?? ''}
              onChange={handleMinPlayersChange}
              min={1}
              max={20}
              size="sm"
            >
              <NumberInputField placeholder="Min" />
            </NumberInput>
            <Text>-</Text>
            <NumberInput
              value={filters.maxPlayers ?? ''}
              onChange={handleMaxPlayersChange}
              min={1}
              max={20}
              size="sm"
            >
              <NumberInputField placeholder="Max" />
            </NumberInput>
          </HStack>
        </Box>

        {/* Mechanics Filter */}
        <Box>
          <Text fontSize="sm" mb={2}>
            Mechanics
          </Text>
          <HStack mb={2}>
            <Select
              placeholder="Select mechanic"
              value={selectedMechanic}
              onChange={(e) => setSelectedMechanic(e.target.value)}
              size="sm"
            >
              {availableMechanics.map(mechanic => (
                <option key={mechanic} value={mechanic}>
                  {mechanic}
                </option>
              ))}
            </Select>
            <Button size="sm" onClick={handleAddMechanic} isDisabled={!selectedMechanic}>
              Add
            </Button>
          </HStack>
          {filters.selectedMechanics.length > 0 && (
            <Wrap spacing={2}>
              {filters.selectedMechanics.map(mechanic => (
                <WrapItem key={mechanic}>
                  <Tag size="sm" colorScheme="blue">
                    <TagLabel>{mechanic}</TagLabel>
                    <TagCloseButton onClick={() => handleRemoveMechanic(mechanic)} />
                  </Tag>
                </WrapItem>
              ))}
            </Wrap>
          )}
        </Box>

        {/* Categories Filter */}
        <Box>
          <Text fontSize="sm" mb={2}>
            Categories
          </Text>
          <HStack mb={2}>
            <Select
              placeholder="Select category"
              value={selectedCategory}
              onChange={(e) => setSelectedCategory(e.target.value)}
              size="sm"
            >
              {availableCategories.map(category => (
                <option key={category} value={category}>
                  {category}
                </option>
              ))}
            </Select>
            <Button size="sm" onClick={handleAddCategory} isDisabled={!selectedCategory}>
              Add
            </Button>
          </HStack>
          {filters.selectedCategories.length > 0 && (
            <Wrap spacing={2}>
              {filters.selectedCategories.map(category => (
                <WrapItem key={category}>
                  <Tag size="sm" colorScheme="purple">
                    <TagLabel>{category}</TagLabel>
                    <TagCloseButton onClick={() => handleRemoveCategory(category)} />
                  </Tag>
                </WrapItem>
              ))}
            </Wrap>
          )}
        </Box>
      </VStack>
    </Box>
  );
}
