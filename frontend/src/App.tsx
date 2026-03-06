import type { FC } from "react";
import { Box, Container, Flex, Heading, HStack, IconButton, Spacer, Text, useColorMode } from "@chakra-ui/react";
import { MoonIcon, SunIcon } from "@chakra-ui/icons";
import { HomeView } from "./views/HomeView";

const appVersion = typeof __APP_VERSION__ !== "undefined" ? __APP_VERSION__ : "dev";
const currentYear = new Date().getFullYear();

const App: FC = () => {
  const { colorMode, toggleColorMode } = useColorMode();

  return (
    <Flex direction="column" minH="100vh" bg="gray.50" _dark={{ bg: "gray.900" }}>
      <Box as="header" borderBottomWidth="1px" bg="white" _dark={{ bg: "gray.800" }}>
        <Container maxW="6xl" py={4}>
          <HStack spacing={4}>
            <Heading size="lg">Multi-MCP Control Plane</Heading>
            <Text fontSize="sm" color="gray.500" _dark={{ color: "gray.400" }}>
              v{appVersion}
            </Text>
            <Spacer />
            <IconButton
              aria-label="Toggle color mode"
              variant="ghost"
              onClick={toggleColorMode}
              icon={colorMode === "light" ? <MoonIcon /> : <SunIcon />}
            />
          </HStack>
        </Container>
      </Box>

      <Box as="main" flex="1" py={8}>
        <Container maxW="6xl">
          <HomeView />
        </Container>
      </Box>

      <Box as="footer" borderTopWidth="1px" bg="white" _dark={{ bg: "gray.800" }}>
        <Container maxW="6xl" py={4}>
          <Text fontSize="sm" color="gray.500" _dark={{ color: "gray.400" }}>
            © {currentYear} Tekgnosis Pty Ltd
          </Text>
        </Container>
      </Box>
    </Flex>
  );
};

export default App;
