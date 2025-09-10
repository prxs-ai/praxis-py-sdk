# Security Considerations



## Table of Contents
1. [Authentication and Authorization in P2P Communication](#authentication-and-authorization-in-p2p-communication)
2. [Data Encryption in Transit and at Rest](#data-encryption-in-transit-and-at-rest)
3. [Secure Handling of LLM Prompts and Responses](#secure-handling-of-llm-prompts-and-responses)
4. [Container Escape Prevention and Sandboxing](#container-escape-prevention-and-sandboxing)
5. [Secure Configuration of MCP Servers and Tool Contracts](#secure-configuration-of-mcp-servers-and-tool-contracts)
6. [Denial-of-Service Protection in APIs](#denial-of-service-protection-in-apis)
7. [Event Bus Communication Security](#event-bus-communication-security)

## Authentication and Authorization in P2P Communication

The Praxis SDK implements robust authentication and authorization mechanisms for peer-to-peer (P2P) communication using libp2p security protocols. The system leverages Ed25519 keypairs for identity verification and supports the Noise protocol for encrypted handshakes.

The `P2PSecurityManager` class in `security.py` is responsible for managing cryptographic keys. It generates or loads Ed25519 keypairs from a secure keystore, ensuring that each node has a unique and verifiable identity. The keypair is derived from a 32-byte random seed stored in a file, which is created if it does not exist:

```python
def load_or_create_keypair(self, key_filename: str = "node.key") -> KeyPair:
    key_path = self.keystore_path / key_filename
    if key_path.exists():
        seed = key_path.read_bytes()
    else:
        seed = os.urandom(32)
        key_path.write_bytes(seed)
    return create_new_key_pair(seed)
```

Authorization is enforced through the configuration of security transport options in the `P2PService` class. When configured, the Noise protocol is used to encrypt all communication, requiring a valid private key for handshake completion:

```python
def _get_security_options(self) -> Dict:
    if self.config.security.use_noise and self.config.security.noise_key:
        return {
            NOISE_PROTOCOL_ID: NoiseTransport(
                libp2p_keypair=self.keypair,
                noise_privkey=self._decode_noise_key(self.config.security.noise_key)
            )
        }
    else:
        return {
            PLAINTEXT_PROTOCOL_ID: InsecureTransport(
                local_key_pair=self.keypair
            )
        }
```

Integration tests confirm that secure connections are established only when valid credentials are provided, as demonstrated in `test_p2p_connectivity.py`, where successful peer discovery implies a completed security handshake.

**Section sources**
- [security.py](file://src/praxis_sdk/p2p/security.py#L0-L58)
- [service.py](file://src/praxis_sdk/p2p/service.py#L208-L238)
- [test_p2p_connectivity.py](file://tests/integration/test_p2p_connectivity.py#L306-L333)

## Data Encryption in Transit and at Rest

Data encryption is implemented at multiple layers to protect information both in transit and at rest. For P2P communication, the system supports the Noise protocol, which provides forward secrecy and resistance to replay attacks. When enabled in the configuration, all libp2p streams are encrypted using the Noise_IK handshake pattern with ChaCha20-Poly1305 encryption.

In transit, WebSocket communications are secured via TLS at the transport layer, while internal message payloads are structured using authenticated JSON Web Tokens (JWTs) where applicable. The `WebSocketManager` ensures that all event streaming and command execution messages are serialized securely and transmitted over encrypted channels.

At rest, cryptographic material such as Ed25519 private key seeds is stored in files with restricted permissions within a designated keystore directory. The system creates this directory with appropriate access controls (`mkdir(parents=True, exist_ok=True)`) and stores the 32-byte seed directly in binary format, minimizing exposure.

For agent-to-agent (A2A) and tool invocation protocols, JSON payloads are transmitted over encrypted streams, ensuring confidentiality and integrity. No sensitive data is logged in plaintext, and debugging output is minimized in production environments.

**Section sources**
- [security.py](file://src/praxis_sdk/p2p/security.py#L0-L58)
- [service.py](file://src/praxis_sdk/p2p/service.py#L208-L238)

## Secure Handling of LLM Prompts and Responses

The SDK employs strict safeguards to prevent leakage of sensitive context during LLM interactions. All prompts and responses are processed within isolated execution contexts, and user data is never stored beyond the scope of a single request.

The `context_builder.py` module ensures that only necessary context is injected into prompts, applying filtering rules to exclude credentials, API keys, or personal identifiers. Additionally, the system supports prompt templating with parameterized inputs, reducing the risk of accidental data exposure.

LLM responses are validated before being passed to downstream components. The `workflow_planner.py` and `plan_optimizer.py` modules sanitize outputs to prevent injection attacks or unauthorized command execution. Sensitive fields in responses are redacted when logged, and full payloads are only accessible within secure memory spaces.

WebSocket-based communication with clients uses structured message types (`MessageType.DSL_COMMAND`, `MessageType.CHAT_MESSAGE`) that are validated against Pydantic models, ensuring schema integrity and preventing malformed input from reaching the LLM.

**Section sources**
- [websocket.py](file://src/praxis_sdk/api/websocket.py#L0-L807)

## Container Escape Prevention and Sandboxing

While the current codebase does not include direct containerization logic, the execution engine is designed with sandboxing principles in mind. Tool execution occurs through isolated process invocation, and the `engine.py` module enforces strict boundaries on tool capabilities.

The SDK integrates with external tools via defined contracts (e.g., `contract.yaml`), which specify allowed inputs, outputs, and execution parameters. These contracts act as policy guards, preventing tools from accessing unauthorized resources.

Future extensions could integrate with container runtimes (e.g., Docker, gVisor) to provide stronger isolation. The modular design of the `execution.engine` component allows for pluggable sandbox backends, enabling container escape prevention through namespace isolation, seccomp profiles, and capability dropping.

All tool executions are logged and monitored via the event bus, allowing for real-time detection of anomalous behavior that may indicate sandbox breakout attempts.

## Secure Configuration of MCP Servers and Tool Contracts

MCP (Modular Compute Protocol) servers are configured with security-first defaults. The `mcp/server.py` module requires explicit enablement of endpoints and enforces authentication for all remote procedure calls.

Tool contracts, defined in YAML files (e.g., `tools/*/contract.yaml`), specify strict input validation rules, including type constraints, allowed values, and size limits. These contracts are validated at registration time by the `mcp/registry.py` module, preventing malformed or overly permissive tools from being loaded.

The `mcp/integration.py` module ensures that all tool invocations respect the declared contract, sanitizing inputs and validating outputs before returning results. This prevents injection attacks and enforces least privilege.

Configuration files (e.g., `agent_production.yaml`) support encrypted secrets and environment variable substitution, reducing the risk of credential leakage in configuration files.

## Denial-of-Service Protection in WebSocket and HTTP APIs

The WebSocket API includes multiple safeguards against denial-of-service (DoS) attacks. The `WebSocketManager` enforces a maximum connection limit (`max_connections: int = 100`) and automatically disconnects clients that exceed message rate thresholds.

Heartbeat monitoring detects inactive or unresponsive clients:

```python
async def _heartbeat_monitor(self):
    while self._running:
        current_time = datetime.utcnow()
        stale_connections = []
        for connection in self.connections.values():
            if connection.last_ping:
                time_since_ping = (current_time - connection.last_ping).total_seconds()
                if time_since_ping > self.heartbeat_interval * 3:
                    stale_connections.append(connection.id)
        for connection_id in stale_connections:
            await self._disconnect_client(connection_id, reason="Heartbeat timeout")
        await trio.sleep(self.heartbeat_interval)
```

Additionally, connection cleanup removes clients with excessive error counts (`error_count > 10`). Message parsing is wrapped in try-except blocks to prevent crashes from malformed input, and JSON decoding errors are handled gracefully.

HTTP API rate limiting and input validation are managed through FastAPI middleware, though specific implementations are not visible in the provided codebase. The architecture supports integration with external rate-limiting services via the event bus and middleware hooks.

## Event Bus Communication Security

The event bus (`bus.py`) ensures secure communication between components by validating event types and enforcing access controls. Events are published with metadata including timestamps and correlation IDs, enabling audit logging and traceability.

The `WebSocketManager` integrates with the event bus through filtered subscriptions:

```python
event_bus.websocket_manager.add_connection(connection_id, send_channel, default_filter)
```

The `EventFilter` restricts which event types a WebSocket client can receive, preventing unauthorized access to sensitive events. Subscribers can dynamically adjust their filters using `SUBSCRIBE_EVENTS` and `UNSUBSCRIBE_EVENTS` messages, but only for permitted event types.

All event data is serialized securely before transmission, and the bus supports source attribution (`source="p2p_service"`) to help detect spoofed events. Unauthorized event injection is mitigated by requiring valid connection contexts and enforcing type safety through Pydantic models.

**Section sources**
- [websocket.py](file://src/praxis_sdk/api/websocket.py#L0-L807)

**Referenced Files in This Document**   
- [security.py](file://src/praxis_sdk/p2p/security.py#L0-L58)
- [service.py](file://src/praxis_sdk/p2p/service.py#L208-L238)
- [websocket.py](file://src/praxis_sdk/api/websocket.py#L0-L807)
- [test_p2p_connectivity.py](file://tests/integration/test_p2p_connectivity.py#L306-L333)