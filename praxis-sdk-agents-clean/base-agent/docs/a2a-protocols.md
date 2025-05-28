# Agent-to-Agent (A2A) Communication Protocols

This document describes the libp2p-based protocols used for direct Agent-to-Agent communication, enabling decentralized interactions without relying on central HTTP endpoints.

## Overview

A2A protocols allow agents to communicate directly with each other through libp2p networking, even when they are behind NATs or firewalls. This approach improves resilience, reduces coupling on HTTP endpoints, and supports the broader decentralized agent ecosystem strategy.

## Protocol: /ai-agent/card/1.0.0

### Description

The `/ai-agent/card/1.0.0` protocol enables agents to request and retrieve model cards (agent metadata) from other agents through direct libp2p streams.

### Purpose

- **Decentralized Discovery**: Agents can discover capabilities of other agents without central registry
- **Resilient Communication**: Works behind NATs and firewalls through libp2p relay mechanisms  
- **Direct Data Exchange**: Eliminates dependency on HTTP endpoints for basic agent information

### Protocol Specification

**Protocol ID**: `/ai-agent/card/1.0.0`

**Transport**: libp2p stream

**Direction**: Request-Response

### Request Format

The request consists of opening a stream to the target agent with the protocol ID. No payload is required.

```
# Open stream with protocol /ai-agent/card/1.0.0
# No request body needed
```

### Response Format

The response is sent as raw bytes over the libp2p stream containing the agent's card data in JSON format.

#### Success Response

```json
{
  "name": "example-agent", 
  "version": "1.0.0",
  "description": "Description of the agent's capabilities",
  "skills": [
    {
      "id": "skill-id",
      "name": "Skill Name", 
      "description": "Skill description",
      "path": "/skill-path",
      "method": "POST",
      "input_model": { "...": "JSON Schema" },
      "output_model": { "...": "JSON Schema" },
      "params_model": { "...": "JSON Schema" }
    }
  ]
}
```

#### Error Response

```json
{
  "error": "Error description",
  "code": 500
}
```

**Error Codes**:
- `404`: Agent card endpoint not found
- `500`: Internal server error
- `503`: Service unavailable  
- `504`: Request timeout or connection error

### Implementation Details

#### Server Side (Agent receiving requests)

1. **Protocol Registration**: Register the stream handler during libp2p initialization
   ```python
   host.set_stream_handler(PROTOCOL_CARD, handle_card)
   ```

2. **Request Processing**: 
   - Extract peer ID from incoming stream
   - Make internal HTTP GET request to `localhost:8000/card`
   - Forward response data through libp2p stream
   - Handle errors and timeouts appropriately
   - Close stream after completion

3. **Error Handling**:
   - HTTP errors → JSON error response with appropriate status code
   - Timeouts → 504 Gateway Timeout
   - Connection errors → 504 Gateway Timeout  
   - Unexpected errors → 500 Internal Server Error

#### Client Side (Agent making requests)

```python
# Example client implementation
async def request_agent_card(host, peer_id):
    try:
        stream = await host.new_stream(peer_id, ["/ai-agent/card/1.0.0"])
        response_data = await stream.read(4096)  # Adjust buffer size as needed
        await stream.close()
        
        card_data = json.loads(response_data.decode())
        return card_data
    except Exception as e:
        print(f"Error requesting card from {peer_id}: {e}")
        return None
```

### Example Exchange

```
1. Client opens stream to Server with protocol "/ai-agent/card/1.0.0"
2. Server receives stream, logs: "Received card request from QmPeerABC..."
3. Server makes HTTP GET to localhost:8000/card  
4. Server receives card data from local FastAPI
5. Server writes card JSON data to libp2p stream
6. Server closes stream, logs: "Sent card data to QmPeerABC..."
7. Client receives card data and processes it
```
