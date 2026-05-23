# AWS S3 Integration & Deployment Strategy Review

**Date:** May 2026
**Topic:** Transitioning from Local File System to AWS S3 for Document Storage

## Overview
As part of our journey to deploy the Database Research RAG system to AWS, we have fundamentally altered how raw PDF documents are handled. We moved away from local storage (`/data/raw_pdfs/`) to cloud-native blob storage using **Amazon S3**.

This document explains the technical nuances, the libraries used, and how the various microservices interact with the new architecture.

---

## 1. The Core Problem
Previously, when an admin uploaded a research paper via the Angular UI, the Go API Gateway would save it directly to the local disk inside the Docker container. 
This created several problems for cloud deployment:
- **Statefulness:** Containers in AWS ECS (Fargate) are ephemeral. If a container restarts, locally saved PDFs are lost.
- **Scaling:** If we run multiple Go API instances behind a load balancer, an uploaded PDF would only exist on one instance, causing 404 errors when a user tries to view it from another instance.

**Solution:** Offload the state to Amazon S3. 

---

## 2. Component Updates

### 2.1 Go API Gateway (`/apps/api`)
The Go API handles the initial upload and file serving. 

*   **Libraries Added:**
    *   `github.com/aws/aws-sdk-go-v2`: The core v2 AWS SDK for Go.
    *   `github.com/aws/aws-sdk-go-v2/service/s3`: Specifically the S3 client.
    *   `github.com/aws/aws-sdk-go-v2/config`: Handles loading credentials seamlessly from environment variables (`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`) or IAM roles.
*   **Upload Flow (`UploadPaper`):** Instead of calling `os.Create()`, the API now takes the incoming multipart file stream and uses `s3.PutObject` to stream the data directly to the bucket defined in `AWS_S3_BUCKET_NAME` under the prefix `raw_pdfs/`.
*   **Serving PDFs (`GetPaperURL`):** We **removed** the local static file server. Instead, when the UI requests a PDF, the Go API uses the `s3.NewPresignClient` to generate an **S3 Pre-signed URL**. 
    *   *Nuance:* The Go API returns an `http.Redirect` (Status 302) to this pre-signed URL. This allows the Angular frontend to remain completely unchanged. It asks the backend for `/pdfs/paper.pdf`, and the backend transparently redirects the browser to a secure, temporary (15-minute) AWS URL.

### 2.2 Python RAG Engine (`/services/ingestion`)
The Python engine runs the `Docling` ingestion pipeline, chunking, and embedding. It previously expected PDFs to exist on the local disk.

*   **Libraries Added:**
    *   `boto3`: The official AWS SDK for Python.
    *   `python-dotenv`: Added to easily load the `.env` file containing the S3 bucket name.
*   **Parsing Flow (`pdf_parser.py`):** 
    *   The `PdfParser` class was updated to initialize a `boto3.client('s3')`.
    *   When asked to parse a document (e.g., `parse_pdf("dynamo.pdf")`), it first checks if the file exists locally.
    *   If it does not exist locally (which is now the expected behavior in production), it uses `tempfile.mkstemp` to create a secure temporary file on the container.
    *   It downloads the PDF from S3 to this temporary file.
    *   It runs the complex `Docling` parsing on the temporary file, saves the JSON output, and then safely deletes the temporary PDF to free up disk space.

---

## 3. Environment Configuration
To make this work in production or locally, the following environment variables are required across the `.env` and `docker-compose.yml` configurations:

```env
AWS_REGION=us-east-1
AWS_S3_BUCKET_NAME=your-production-bucket-name
# The following are only needed for local dev. 
# In AWS ECS, we use IAM Task Roles instead of hardcoded keys.
AWS_ACCESS_KEY_ID=xxxx
AWS_SECRET_ACCESS_KEY=xxxx
```

## 4. Next Steps for Full Deployment
Now that the application's state (Database = PostgreSQL, Vectors = ChromaDB/EFS, Files = S3) is decoupled from the compute containers, we are ready for **Phase 2: Terraform**.

The upcoming Terraform code will provision:
1.  **Networking:** A VPC with Public and Private subnets.
2.  **S3:** The bucket for the PDFs.
3.  **RDS:** A managed PostgreSQL database.
4.  **ECS Fargate:** Serverless container execution for the Go API, Python Engine, and Nginx UI.
5.  **ALB:** An Application Load Balancer to route traffic to the services.
