# Architecture Blueprint

This document defines the physical and logical architecture for the Database Research RAG deployment on AWS.

## Logical Architecture Layers

1. **Presentation Layer (Apps)**
   - **UI (`/apps/ui`):** A modern web interface built with **Angular** for users to submit queries and view responses with cited sources.
   - **API (`/apps/api`):** High-performance REST/GraphQL API built with **Golang** serving the UI.

2. **Application Logic Layer (Services)**
   - Orchestrates the RAG workflow.
   - Receives query -> Calls Retrieval Engine -> Formats Prompt -> Calls LLM -> Returns Response.

3. **Retrieval Layer**
   - Coordinates the hybrid search.
   - Interfaces with OpenSearch for BM25 and Vector search.
   - Calls the Cross-Encoder model for reranking.

4. **Data & Storage Layer**
   - **AWS S3:** Object storage for PDFs, parsed JSON, and intermediate artifacts.
   - **AWS OpenSearch Serverless:** The core search engine holding the vector index and keyword index.
   - **DynamoDB (Optional):** For storing user session history and cached responses.

## Physical AWS Architecture

```mermaid
graph TD;
    Client-->API_Gateway;
    API_Gateway-->Lambda_RAG_Service;
    Lambda_RAG_Service-->OpenSearch_Cluster;
    Lambda_RAG_Service-->LLM_API[OpenAI/Anthropic API];
    Lambda_RAG_Service-->SageMaker_Reranker[SageMaker Endpoint (Cross-Encoder)];
    
    Ingestion_Pipeline-->S3_Raw_PDFs;
    S3_Raw_PDFs-->Lambda_Parser;
    Lambda_Parser-->S3_Parsed_Data;
    S3_Parsed_Data-->Batch_Embedder[ECS/Fargate Task];
    Batch_Embedder-->OpenSearch_Cluster;
```

## Security & Access Control
- **IAM Roles:** Strict least-privilege IAM roles for all Lambda functions and ECS tasks.
- **VPC:** OpenSearch cluster must reside in a private VPC subnet.
- **API Security:** API Gateway secured via AWS Cognito or API Keys for rate limiting and authentication.

## Scalability Considerations
- **Ingestion:** Use AWS Step Functions to orchestrate the ingestion pipeline (Parsing -> Chunking -> Embedding) to handle parallel processing of hundreds of PDFs.
- **Retrieval:** OpenSearch handles scaling the search index. Ensure proper shard allocation based on index size.
- **Generation:** Use asynchronous LLM API calls. Implement fallback logic (e.g., switch from GPT-4 to GPT-3.5) if the primary model hits rate limits.