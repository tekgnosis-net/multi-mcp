import type { FC } from "react";
import { Badge, Box, Divider, HStack, Heading, List, ListItem, Stack, Text } from "@chakra-ui/react";
import type { MCPServerOverview } from "../api/client";

interface ServerOverviewCardProps {
  name: string;
  overview: MCPServerOverview;
}

export const ServerOverviewCard: FC<ServerOverviewCardProps> = ({ name, overview }) => {
  const { stats, tools, connected } = overview;

  return (
    <Box borderWidth="1px" borderRadius="lg" p={4} bg="white" _dark={{ bg: "gray.800" }} h="100%">
      <Stack spacing={3}>
        <HStack justify="space-between" align="baseline">
          <Heading size="md">{name}</Heading>
          <Badge colorScheme={connected ? "green" : "red"}>{connected ? "Connected" : "Offline"}</Badge>
        </HStack>
        <Text fontSize="sm" color="gray.500" _dark={{ color: "gray.400" }}>
          Tools: {stats.tools} · Prompts: {stats.prompts} · Resources: {stats.resources}
        </Text>
        <Divider />
        <Stack spacing={2}>
          <Text fontWeight="semibold">Tools</Text>
          {tools.length === 0 ? (
            <Text fontSize="sm" color="gray.500" _dark={{ color: "gray.400" }}>
              No tools reported.
            </Text>
          ) : (
            <List spacing={1} fontFamily="mono" fontSize="sm">
              {tools.map((tool) => (
                <ListItem key={tool}>{tool}</ListItem>
              ))}
            </List>
          )}
        </Stack>
        {stats.last_error && (
          <Box borderWidth="1px" borderColor="red.200" _dark={{ borderColor: "red.400" }} borderRadius="md" p={2}>
            <Text fontSize="sm" color="red.600" _dark={{ color: "red.300" }}>
              Last error: {stats.last_error}
            </Text>
          </Box>
        )}
        {stats.last_invoked_at && (
          <Text fontSize="xs" color="gray.500" _dark={{ color: "gray.400" }}>
            Last tool invocation: {new Date(stats.last_invoked_at).toLocaleString()}
          </Text>
        )}
      </Stack>
    </Box>
  );
};
