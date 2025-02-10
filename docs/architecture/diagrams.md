# UMBRELLA-AI Architecture Diagrams

## System Overview

```mermaid
graph TB
    Client[Client Applications] --> Gateway[API Gateway]
    Gateway --> Auth[Authentication Service]
    Gateway --> Orchestrator[Orchestrator Service]
    
    subgraph "AI Agents"
        Orchestrator --> PDF[PDF Extraction Agent]
        Orchestrator --> Sentiment[Sentiment Analysis Agent]
        Orchestrator --> Recommend[Recommendation Agent]
        Orchestrator --> Chat[Chatbot Agent]
        Orchestrator --> RAG[RAG Scraper Agent]
    end
    
    subgraph "Data Storage"
        MongoDB[(MongoDB)]
        VectorDB[(ChromaDB)]
        Redis[(Redis Cache)]
    end
    
    subgraph "Message Queue"
        RabbitMQ{RabbitMQ}
    end
    
    PDF --> VectorDB
    Sentiment --> VectorDB
    Recommend --> MongoDB
    Chat --> Redis
    RAG --> VectorDB
    
    Orchestrator <--> RabbitMQ
    AI Agents <--> RabbitMQ
```

## Request Flow

```mermaid
sequenceDiagram
    participant C as Client
    participant G as API Gateway
    participant O as Orchestrator
    participant A as AI Agents
    participant Q as RabbitMQ
    participant D as Databases

    C->>G: API Request
    G->>O: Authenticated Request
    O->>O: Task Decomposition
    O->>Q: Publish Tasks
    Q->>A: Consume Tasks
    A->>D: Read/Write Data
    A->>Q: Publish Results
    Q->>O: Aggregate Results
    O->>G: Final Response
    G->>C: API Response
```

## Deployment Architecture

```mermaid
graph TB
    subgraph "AWS Cloud"
        ALB[Application Load Balancer]
        
        subgraph "ECS/EKS Cluster"
            API[API Gateway Service]
            Auth[Auth Service]
            Orch[Orchestrator Service]
            Agents[AI Agent Services]
        end
        
        subgraph "Data Layer"
            RDS[(MongoDB)]
            ElastiCache[(Redis)]
            S3[(S3 Storage)]
        end
        
        subgraph "Message Queue"
            MQ[RabbitMQ Cluster]
        end
        
        subgraph "Monitoring"
            Prom[Prometheus]
            Graf[Grafana]
            Logs[CloudWatch]
        end
    end
    
    Internet((Internet)) --> ALB
    ALB --> API
    API --> Auth
    API --> Orch
    Orch --> Agents
    Agents --> RDS
    Agents --> ElastiCache
    Agents --> S3
    Orch <--> MQ
    Agents <--> MQ
    
    ECS/EKS Cluster --> Prom
    Prom --> Graf
    ECS/EKS Cluster --> Logs
```

## Data Model

```mermaid
erDiagram
    USER ||--o{ DOCUMENT : uploads
    USER ||--o{ QUERY : makes
    DOCUMENT ||--o{ ANALYSIS : generates
    QUERY ||--o{ RESPONSE : receives
    
    USER {
        string id PK
        string name
        string email
        datetime created_at
    }
    
    DOCUMENT {
        string id PK
        string user_id FK
        string type
        string content
        datetime uploaded_at
    }
    
    ANALYSIS {
        string id PK
        string document_id FK
        string type
        json results
        datetime created_at
    }
    
    QUERY {
        string id PK
        string user_id FK
        string content
        datetime created_at
    }
    
    RESPONSE {
        string id PK
        string query_id FK
        json content
        datetime created_at
    }
``` 