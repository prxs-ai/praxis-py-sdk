# Agent Containers

The SDK agent service is composed of three primary containers working together at runtime.

- **SDK Library** – houses bootstrap code and configuration helpers. When the service starts, this layer instantiates the runtime and any adapters based on entry points.
- **Agent Runtime** – the core execution engine built on Ray Serve and LangChain. It handles plan generation, workflow execution, memory management and message processing.
- **Plugin/Adapter Layer** – a collection of adapters for tools or other agents. Each adapter exposes a simple interface and is invoked by the runtime when a workflow step requires external functionality.

At startup the SDK Library boots the Agent Runtime with the configured adapters. During request processing the Agent Runtime calls the relevant adapter (synchronously over HTTP or direct SDK call) to perform a tool action. Results flow back to the runtime which then returns a response to the caller.
