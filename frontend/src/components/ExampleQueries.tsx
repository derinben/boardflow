import { Wrap, WrapItem, Tag, Text, Box } from '@chakra-ui/react';

interface ExampleQueriesProps {
  onExampleClick: (query: string) => void;
}

const EXAMPLE_QUERIES = [
  'I like Catan and 7 Wonders, want something with trading',
  'Games for 6+ players that are easy to learn',
  'Complex strategy games similar to Twilight Imperium',
  'Quick card games for 2 players',
  'Cooperative games with storytelling',
];

/**
 * Clickable example queries to help users understand what to search for
 *
 * When clicked, fills the search input with the example query
 */
export default function ExampleQueries({ onExampleClick }: ExampleQueriesProps) {
  return (
    <Box>
      <Text fontSize="sm" color="gray.600" mb={2}>
        Try an example:
      </Text>
      <Wrap spacing={2}>
        {EXAMPLE_QUERIES.map((example, index) => (
          <WrapItem key={index}>
            <Tag
              size="md"
              variant="subtle"
              colorScheme="blue"
              cursor="pointer"
              onClick={() => onExampleClick(example)}
              _hover={{ bg: 'blue.100' }}
            >
              {example}
            </Tag>
          </WrapItem>
        ))}
      </Wrap>
    </Box>
  );
}
