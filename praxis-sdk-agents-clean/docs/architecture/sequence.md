# Sequence Diagrams

The following diagrams outline typical interactions with the SDK agent.

- **bootstrapping.mmd** – shows how the agent initializes its workflow runner and connects to the relay when the service starts.

```mermaid
sequenceDiagram
    participant Bootstrap
    participant WorkflowRunner as Runner
    participant Relay

    Bootstrap->>Runner: start_daemon()
    Bootstrap->>Runner: run_background_workflows()
    Bootstrap->>Relay: start()
    Relay-->>Bootstrap: connected
    Bootstrap-->>Bootstrap: agent ready
```

- **tool-interaction.mmd** – depicts the agent receiving a user request and invoking an external tool to fulfil it.

```mermaid
sequenceDiagram
    participant User
    participant AgentAPI as Agent
    participant Tool

    User->>AgentAPI: user query
    AgentAPI->>Tool: call service
    Tool-->>AgentAPI: result
    AgentAPI-->>User: response
```

- **agent-handoff.mmd** – illustrates one agent delegating a request to another via the relay service and returning the result.

```mermaid
sequenceDiagram
    participant AgentA
    participant Relay
    participant AgentB

    AgentA->>Relay: handoff(goal, plan)
    Relay->>AgentB: deliver request
    AgentB->>Relay: result
    Relay->>AgentA: result
    AgentA-->>Caller: finalize
```


- **user-chat.mmd** – demonstrates the conversational flow where a user message is classified, triggers a tool call and the agent replies back.

```mermaid
sequenceDiagram
    participant User
    participant Agent
    participant Classifier
    participant Tool

    User->>Agent: message
    Agent->>Classifier: classify intent
    Classifier-->>Agent: intent
    Agent->>Tool: call tool
    Tool-->>Agent: response
    Agent-->>User: answer
```