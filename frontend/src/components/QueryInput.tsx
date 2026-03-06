import { FormControl, Input, Button, HStack, FormErrorMessage } from '@chakra-ui/react';
import { SearchIcon } from '@chakra-ui/icons';

interface QueryInputProps {
  query: string;
  onQueryChange: (query: string) => void;
  onSearch: () => void;
  loading: boolean;
  error: string | null;
}

/**
 * Search input component with submit button
 *
 * Features:
 * - Text input for natural language queries
 * - Submit button (or press Enter)
 * - Loading state during API call
 * - Error message display
 * - Validation (1-1000 chars)
 */
export default function QueryInput({ query, onQueryChange, onSearch, loading, error }: QueryInputProps) {
  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !loading) {
      onSearch();
    }
  };

  const isInvalid = error !== null;

  return (
    <FormControl isInvalid={isInvalid}>
      <HStack spacing={2}>
        <Input
          placeholder="Describe what you're looking for (e.g., 'I like Catan, want something with trading')"
          value={query}
          onChange={(e) => onQueryChange(e.target.value)}
          onKeyPress={handleKeyPress}
          size="lg"
          disabled={loading}
        />
        <Button
          leftIcon={<SearchIcon />}
          colorScheme="blue"
          size="lg"
          onClick={onSearch}
          isLoading={loading}
          loadingText="Searching"
          isDisabled={!query.trim() || query.length > 1000}
        >
          Search
        </Button>
      </HStack>
      {isInvalid && <FormErrorMessage>{error}</FormErrorMessage>}
    </FormControl>
  );
}
