import { useCallback, useEffect, useState, type FC } from "react";
import {
  Alert,
  AlertIcon,
  Box,
  Button,
  Heading,
  HStack,
  SimpleGrid,
  Spinner,
  Stack,
  Text,
  useToast,
} from "@chakra-ui/react";
import {
  fetchConfig,
  fetchServers,
  updateConfig,
  type MCPConfig,
  type MCPServerOverview,
} from "../api/client";
import { ConfigEditor } from "../components/ConfigEditor";
import { ServerOverviewCard } from "../components/ServerOverviewCard";

export const HomeView: FC = () => {
  const toast = useToast();
  const [servers, setServers] = useState<Record<string, MCPServerOverview>>({});
  const [config, setConfig] = useState<MCPConfig | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [serversData, configData] = await Promise.all([fetchServers(), fetchConfig()]);
      setServers(serversData);
      setConfig(configData);
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err);
      setError(message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadData();
  }, [loadData]);

  const handleRefresh = async () => {
    await loadData();
    toast({
      status: "info",
      title: "Refreshed",
      description: "Latest server state fetched.",
      duration: 2000,
      isClosable: true,
    });
  };

  const handleSaveConfig = async (nextConfig: MCPConfig) => {
    setSaving(true);
    try {
      await updateConfig(nextConfig);
      setConfig(nextConfig);
      await loadData();
      toast({
        status: "success",
        title: "Configuration updated",
      });
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err);
      toast({ status: "error", title: "Failed to save config", description: message });
    } finally {
      setSaving(false);
    }
  };

  if (loading && !config) {
    return (
      <Box textAlign="center" py={16}>
        <Spinner size="xl" />
        <Text mt={4}>Loading MCP data…</Text>
      </Box>
    );
  }

  return (
    <Stack spacing={8}>
      <HStack justify="space-between" align="baseline">
        <Heading size="md">Active MCP Servers</Heading>
        <Button onClick={() => void handleRefresh()} variant="outline" size="sm">
          Refresh
        </Button>
      </HStack>

      {error && (
        <Alert status="error" borderRadius="md">
          <AlertIcon />
          {error}
        </Alert>
      )}

      <SimpleGrid columns={{ base: 1, md: 2 }} spacing={6}>
        {(Object.entries(servers) as [string, MCPServerOverview][]).map(([name, overview]) => (
          <ServerOverviewCard key={name} name={name} overview={overview} />
        ))}
        {Object.keys(servers).length === 0 && (
          <Box borderWidth="1px" borderRadius="lg" p={6} textAlign="center" bg="white" _dark={{ bg: "gray.800" }}>
            <Text>No MCP backends configured yet.</Text>
          </Box>
        )}
      </SimpleGrid>

      <Stack spacing={4}>
        <Heading size="md">Configuration</Heading>
        <ConfigEditor config={config} onSubmit={handleSaveConfig} isSubmitting={saving} />
      </Stack>
    </Stack>
  );
};
