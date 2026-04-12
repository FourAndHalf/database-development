# Concepts Map

This document outlines the interconnected graph of database concepts. It acts as a reference for Query Expansion: when a user asks about Concept A, the retrieval system should also look for Concept B.

## Core Relationships

### B-Tree -> LSM-Tree
- **Relationship:** Evolution/Alternative. B-Trees optimize for reads and in-place updates; LSM-Trees optimize for high write throughput using sequential I/O.
- **Linked Papers:** InnoDB (B-Tree) vs. The Log-Structured Merge-Tree (LSM).

### Paxos -> Raft
- **Relationship:** Simplification/Pedagogy. Raft was explicitly designed to be more understandable than Paxos while providing the same safety guarantees.
- **Linked Papers:** Paxos Made Simple vs. In Search of an Understandable Consensus Algorithm (Raft).

### Dynamo -> Cassandra
- **Relationship:** Architectural lineage. Cassandra borrows Dynamo's distributed architecture (Consistent Hashing, Gossip, Sloppy Quorums) but uses a Bigtable-like data model (Column families).
- **Linked Papers:** Dynamo vs. Cassandra vs. Bigtable.

### TrueTime -> Linearizability
- **Relationship:** Implementation mechanism. Spanner uses the TrueTime API (GPS + Atomic clocks) to achieve External Consistency (Linearizability) across a globally distributed system.
- **Linked Papers:** Spanner.

### Vector Clocks -> Eventual Consistency
- **Relationship:** Conflict resolution mechanism. Systems that sacrifice strong consistency for availability (like Dynamo) use Vector Clocks to track causality and detect concurrent updates.
- **Linked Papers:** Dynamo.

## Implementation in RAG
The `Query Analyzer` uses a programmatic version of this map to inject synonyms and related terms into the keyword search (BM25) to increase Recall.