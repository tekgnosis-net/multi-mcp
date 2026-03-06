import { useState, useEffect, type FC } from "react";
import { Box, Button, FormControl, FormLabel, Textarea, VStack, Alert, AlertIcon } from "@chakra-ui/react";
import type { MCPConfig } from "../api/client";

interface ConfigEditorProps {
  config: MCPConfig | null;
  onSubmit: (nextConfig: MCPConfig) => Promise<void>;
  isSubmitting: boolean;
}

export const ConfigEditor: FC<ConfigEditorProps> = ({ config, onSubmit, isSubmitting }) => {
  const [inputValue, setInputValue] = useState("");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (config) {
      setInputValue(JSON.stringify(config, null, 2));
      setError(null);
    }
  }, [config]);

  const handleSubmit = async () => {
    if (!inputValue.trim()) {
      setError("Configuration cannot be empty");
      return;
    }

    try {
      const parsed = JSON.parse(inputValue) as MCPConfig;
      if (!parsed.mcpServers || typeof parsed.mcpServers !== "object") {
        throw new Error("Config must include an 'mcpServers' object");
      }
      setError(null);
      await onSubmit(parsed);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  };

  return (
    <Box borderWidth="1px" borderRadius="lg" p={4} bg="white" _dark={{ bg: "gray.800" }}>
      <VStack align="stretch" spacing={4}>
        <FormControl>
          <FormLabel>Configuration (JSON)</FormLabel>
          <Textarea
            minH="240px"
            fontFamily="mono"
            value={inputValue}
            onChange={(event) => setInputValue(event.target.value)}
            isDisabled={!config || isSubmitting}
          />
        </FormControl>
        {error && (
          <Alert status="error" borderRadius="md">
            <AlertIcon />
            {error}
          </Alert>
        )}
        <Button colorScheme="blue" onClick={handleSubmit} isLoading={isSubmitting} isDisabled={!config}>
          Save Configuration
        </Button>
      </VStack>
    </Box>
  );
};
