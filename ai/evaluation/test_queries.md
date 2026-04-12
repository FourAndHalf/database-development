# Standard Test Queries

This document contains the golden set of test queries used for automated and manual evaluation of the RAG system. These queries are designed to stress-test different capabilities of the pipeline.

## Category 1: Fact Retrieval (Single Document)
*Tests the system's ability to locate a specific fact in a specific paper.*
1. "What is the chunk size used in the Google File System (GFS)?"
2. "In the Dynamo paper, what is the purpose of the Merkle tree?"
3. "According to the Spanner paper, what is the uncertainty bound of TrueTime?"
4. "Who are the authors of the original CAP theorem paper?"

## Category 2: Conceptual Explanation
*Tests the system's ability to synthesize a complex concept from one or multiple chunks.*
1. "Explain the difference between a Paxos Proposer and an Acceptor."
2. "How does a Log-Structured Merge (LSM) tree handle compactions?"
3. "What does 'consistent hashing' mean, and why is it useful in distributed databases?"
4. "Explain the PACELC theorem and how it extends CAP."

## Category 3: Comparative Analysis (Multi-Document)
*Tests the system's ability to retrieve from multiple distinct papers and synthesize a comparison.*
1. "Compare the approach to clock synchronization in Google Spanner versus Amazon Dynamo."
2. "What are the architectural differences between Bigtable and Cassandra?"
3. "Contrast the consensus mechanisms of Raft and Multi-Paxos."
4. "How do the storage layers of C-Store and a traditional InnoDB engine differ?"

## Category 4: Edge Cases & Adversarial Queries
*Tests the system's guardrails against hallucination and out-of-domain answering.*
1. "How do I configure a Snowflake data warehouse?" *(Expected: Rejection, out of domain)*
2. "Which database is better, Spanner or Dynamo?" *(Expected: Objective comparison of tradeoffs, no subjective judgment)*
3. "Did the Raft paper prove that Paxos is fundamentally flawed?" *(Expected: Nuanced answer based *only* on the text, Raft claims Paxos is hard to understand, not logically flawed)*
4. "Write a Python script to connect to a DynamoDB instance." *(Expected: Rejection, system provides research synthesis, not code generation unless explicitly covered in a paper).*