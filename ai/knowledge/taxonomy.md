# Database Research Taxonomy

This document provides the hierarchical taxonomy used by the RAG system to categorize academic papers and concepts. AI agents should use this taxonomy when adding new metadata or structuring retrieval strategies.

## 1. Distributed Systems Fundamentals
- **Consensus Algorithms:** Paxos, Raft, Viewstamped Replication, Epaxos.
- **Clock Synchronization:** Logical Clocks, Vector Clocks, TrueTime (Atomic Clocks).
- **Failure Models:** Crash-Stop, Byzantine Faults, Network Partitions.

## 2. Consistency Models (The Consistency Spectrum)
- **Strong Consistency:** Linearizability, Strict Serializable, Sequential Consistency.
- **Weak/Eventual Consistency:** Causal Consistency, Read-Your-Writes, Monotonic Reads.
- **Theorems:** CAP Theorem, PACELC, CALM.

## 3. Storage Engines (Node-Level Architecture)
- **Log-Structured:** LSM-Trees, Bitcask, WiscKey.
- **In-Place Update:** B-Trees, B+ Trees, InnoDB.
- **Columnar:** C-Store, Dremel (Parquet/ORC lineage).
- **In-Memory:** Hyper, Memcached architectures.

## 4. Distributed Database Architectures
- **Key-Value Stores:** Dynamo, RocksDB (as embedded KV).
- **Wide-Column / Tabular:** Bigtable, Cassandra.
- **Distributed SQL (NewSQL):** Spanner, CockroachDB, F1.
- **Analytical (OLAP):** Madlib, Dremel.

## Usage in Metadata
When new PDFs are ingested, the `pdf_parser.py` attempts to assign one or more of these taxonomic tags to the document metadata. This allows the Retrieval Engine to filter searches (e.g., "Search only within `Consistency Models` for queries about CAP").