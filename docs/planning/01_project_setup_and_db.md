# Phase 1: Project Setup & Database Layer

## 🎯 Objective

Establish the foundational project structure, configure the serverless PostgreSQL database (NeonDB) for metadata, and set up Cloud Storage (e.g., Cloudflare R2) for high-frequency telemetry data.

## 🛠 Required Work

### 1. Project Initialization

- [ ] Initialize Python backend (e.g., using Poetry or generic `requirements.txt`/`pyproject.toml`).
- [ ] Configure linting, formatting, and type-checking (Ruff, Black, MyPy).
- [ ] Set up environment variables handling (`.env` validation with Pydantic Settings, including Postgres URIs and S3/R2 Bucket Credentials).

### 2. Database & Cloud Storage Provisioning

- [ ] Provision a NeonDB instance (Free Tier is sufficient for Metadata).
- [ ] Provision an S3-compatible Object Storage Bucket (Cloudflare R2 recommended for generous 10GB free tier and zero egress fees).
- [ ] Select and configure database migration tool (Alembic).
- [ ] Setup SQLAlchemy 2.0 or SQLModel to act as the relational bridge.

### 3. Schema Implementation (Hybrid)

Implement the relational database schema while ensuring it points to our Data Lake:

- [ ] `races`
- [ ] `drivers`
- [ ] `stints`
- [ ] `laps` (Must include the `telemetry_file_path` column to store the R2 bucket key for that specific lap's `.parquet` file).
- [ ] `micro_sectors` (Optional, mathematical corner records).

### 4. Repository & Storage Interface

- [ ] Create repository interfaces for NeonDB operations.
- [ ] Create an S3/R2 client interface utilizing `boto3` or `aioboto3` to stream and upload`.parquet` blobs seamlessly for the simulation engine.
