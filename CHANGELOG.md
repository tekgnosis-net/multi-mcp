## [1.0.5](https://github.com/tekgnosis-net/multi-mcp/compare/v1.0.4...v1.0.5) (2026-03-06)


### Bug Fixes

* **docker:** use JSON exec form for CMD to ensure proper signal handling ([575b5e2](https://github.com/tekgnosis-net/multi-mcp/commit/575b5e2c9a8c88ac74f10a3220ec582257983bb3))

## [1.0.4](https://github.com/tekgnosis-net/multi-mcp/compare/v1.0.3...v1.0.4) (2026-03-06)


### Bug Fixes

* **client:** shield stack.aclose() from anyio cancellation during hot-reload ([9c5cd6b](https://github.com/tekgnosis-net/multi-mcp/commit/9c5cd6bf37ef6042b731fb5a4fde1d69a4e746f3))

## [1.0.3](https://github.com/tekgnosis-net/multi-mcp/compare/v1.0.2...v1.0.3) (2026-03-06)


### Bug Fixes

* **logging:** suppress watchfiles rust notify timeout debug spam ([effaad7](https://github.com/tekgnosis-net/multi-mcp/commit/effaad7574a824aa8b48f5c62ab4e943afa6cb7f))

## [1.0.2](https://github.com/tekgnosis-net/multi-mcp/compare/v1.0.1...v1.0.2) (2026-03-06)


### Bug Fixes

* **deps:** remove langchain/openai example-only deps that conflict with mcp==1.26.0 ([055294a](https://github.com/tekgnosis-net/multi-mcp/commit/055294a6020da1c579e530ba95b90240698910eb))

## [1.0.1](https://github.com/tekgnosis-net/multi-mcp/compare/v1.0.0...v1.0.1) (2026-03-06)


### Bug Fixes

* **ci:** split docker build into separate job to avoid semantic-release exit code dependency ([f52890e](https://github.com/tekgnosis-net/multi-mcp/commit/f52890eefe699a8b0ed4e6cc9a2b8b40f7809b39))

# 1.0.0 (2026-03-06)


### Bug Fixes

* Add capability checks for prompts and resources in MCP proxy ([3cc95ec](https://github.com/tekgnosis-net/multi-mcp/commit/3cc95ecf7cc81fe640de4d40961cfbf1abb1093f))
* add conventional-changelog-conventionalcommits to semantic-release plugins ([ce30e46](https://github.com/tekgnosis-net/multi-mcp/commit/ce30e46687466e3781aca0b99fae675ff9d7b362))
* Correct investigation filename format ([ad43150](https://github.com/tekgnosis-net/multi-mcp/commit/ad431500aaa1b173c053133fbcde17044677695c))
* Move investigation to correct location claude/250627114051/ ([0955aaf](https://github.com/tekgnosis-net/multi-mcp/commit/0955aaf44e029730e223061fcb632e398d33a7f3))
* Replace :: with _ in tool naming for Claude API compliance ([81c89b7](https://github.com/tekgnosis-net/multi-mcp/commit/81c89b7c6482b5de3d5b4714134e5f8c58ab1fab))
* Switch Dockerfile from Alpine to Debian slim to resolve tiktoken build issues ([fb54d13](https://github.com/tekgnosis-net/multi-mcp/commit/fb54d137170327d9c23f26c462361378c0eebdc2))
* Switch Dockerfile from Alpine to Debian slim to resolve tiktoken build issues ([2f55099](https://github.com/tekgnosis-net/multi-mcp/commit/2f55099b89faeedbb9fb220449608053f8380258))


### Features

* upgrade to mcp 1.26.0, streamable HTTP transport, config hot-reload, and optimised Docker build ([a00d5af](https://github.com/tekgnosis-net/multi-mcp/commit/a00d5af0c1eda6ba55db2c658618bbdc51b0de5a))

# Changelog

All notable changes to this project will be documented here by semantic-release.
