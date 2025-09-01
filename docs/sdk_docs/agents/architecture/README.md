# Architecture Overview

This folder contains high level diagrams for the SDK agent. The context diagram shows how the agent fits inside the wider platform and who interacts with it. The container diagram focuses on the internal pieces that make up the running service.

## Context

- **End User** – interacts with the agent through the HTTP API to ask questions or issue commands.
- **SDK Agent** – the running service hosting the agent logic. It communicates with the AI Registry to discover other agents and tools and uses the Relay Service for peer‑to‑peer messages. When a task requires an external capability the agent invokes a Third‑Party API as a tool.
- **AI Registry** – catalog of available agents and tools. The SDK agent queries it to find the right component for a given goal.
- **Relay Service** – networking layer that connects agents together. Messages such as handoff requests pass through it.
- **Third‑Party API** – any external service the agent calls as part of a workflow, e.g., a weather service.

