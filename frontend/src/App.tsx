import { useState } from 'react';
import { Container, VStack, Heading, Box } from '@chakra-ui/react';
import { useRecommendations } from './hooks/useRecommendations';
import { applyFilters, sortGames, extractUniqueMechanics, extractUniqueCategories } from './utils/filters';
import type { GameFilters, SortOption } from './utils/filters';
import type { GameRecommendation } from './types/api';
import QueryInput from './components/QueryInput';
import ExampleQueries from './components/ExampleQueries';
import ResultsHeader from './components/ResultsHeader';
import FilterBar from './components/FilterBar';
import GameGrid from './components/GameGrid';
import ComparisonBar from './components/ComparisonBar';

function App() {
  // Search state (from custom hook)
  const { query, setQuery, results, loading, error, fetchRecommendations } = useRecommendations();

  // Filter state
  const [filters, setFilters] = useState<GameFilters>({
    complexityRange: [1, 5],
    minPlayers: null,
    maxPlayers: null,
    selectedMechanics: [],
    selectedCategories: [],
  });

  // Sort state
  const [sortBy, setSortBy] = useState<SortOption>('score');

  // Comparison state
  const [selectedGames, setSelectedGames] = useState<number[]>([]);

  // Apply filters and sorting to results
  const filteredResults = applyFilters(results, filters);
  const displayedResults = sortGames(filteredResults, sortBy);

  // Extract unique mechanics/categories for filter dropdowns
  const availableMechanics = results.length > 0 ? extractUniqueMechanics(results) : [];
  const availableCategories = results.length > 0 ? extractUniqueCategories(results) : [];

  // Handlers
  const handleSearch = () => {
    fetchRecommendations();
  };

  const handleExampleClick = (exampleQuery: string) => {
    setQuery(exampleQuery);
  };

  const handleToggleSelection = (gameId: number) => {
    setSelectedGames(prev =>
      prev.includes(gameId)
        ? prev.filter(id => id !== gameId)
        : [...prev, gameId]
    );
  };

  const handleRemoveFromComparison = (gameId: number) => {
    setSelectedGames(prev => prev.filter(id => id !== gameId));
  };

  const getSelectedGamesData = (): GameRecommendation[] => {
    return displayedResults.filter(game => selectedGames.includes(game.id));
  };

  return (
    <Container maxW="container.xl" py={8}>
      <VStack spacing={6} align="stretch">
        {/* Header */}
        <Box textAlign="center">
          <Heading as="h1" size="2xl" mb={2}>
            BoardFlow
          </Heading>
          <Heading as="h2" size="md" fontWeight="normal" color="gray.600">
            Discover your next favorite board game
          </Heading>
        </Box>

        {/* Search Input */}
        <QueryInput
          query={query}
          onQueryChange={setQuery}
          onSearch={handleSearch}
          loading={loading}
          error={error}
        />

        {/* Example Queries */}
        <ExampleQueries onExampleClick={handleExampleClick} />

        {/* Results Section */}
        {results.length > 0 && (
          <>
            {/* Results Header with count and sort */}
            <ResultsHeader
              totalCount={results.length}
              filteredCount={displayedResults.length}
              sortBy={sortBy}
              onSortChange={setSortBy}
            />

            {/* Filters */}
            <FilterBar
              filters={filters}
              onFiltersChange={setFilters}
              availableMechanics={availableMechanics}
              availableCategories={availableCategories}
            />

            {/* Game Grid */}
            <GameGrid
              games={displayedResults}
              selectedGames={selectedGames}
              onToggleSelection={handleToggleSelection}
            />
          </>
        )}

        {/* Comparison Bar (fixed at bottom when games selected) */}
        {selectedGames.length > 0 && (
          <ComparisonBar
            selectedGames={getSelectedGamesData()}
            onRemoveGame={handleRemoveFromComparison}
            onClearAll={() => setSelectedGames([])}
          />
        )}
      </VStack>
    </Container>
  );
}

export default App;
