# Base Agent

A Ray-based agent system with PostgreSQL, Redis, MinIO, and LightRAG integration.

## Components

- **Ray Head**: Distributed computing head node
- **Ray Worker**: Worker node for agent execution  
- **PostgreSQL**: Database storage
- **Redis**: Cache and message broker
- **MinIO**: Object storage
- **LightRAG**: Knowledge base and RAG system

## Usage

```bash
docker-compose --env-file .env up --build
```

## Services

- Ray Dashboard: http://localhost:8265
- LightRAG: http://localhost:8080  
- MinIO Console: http://localhost:9001
