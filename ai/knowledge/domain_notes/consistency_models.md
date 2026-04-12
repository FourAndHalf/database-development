# Domain Note: Consistency Models

This note provides the technical guardrails and definitions for "Consistency" within the context of database research. The RAG LLM must adhere to these precise definitions.

## The Ambiguity of "Consistency"
**CRITICAL:** The term "Consistency" is overloaded in computer science. The LLM must determine context:
1. **ACID Consistency (Database Consistency):** Refers to application-defined rules (e.g., a bank transfer must balance). A transaction brings the database from one valid state to another.
2. **CAP Consistency (Distributed Consistency):** Refers to *Linearizability*. Every read receives the most recent write or an error. It is about the illusion of a single, instantaneous copy of the data.

## Strong Consistency Models
- **Linearizability:** The strongest model. Operations appear to happen instantaneously at a specific point in real-time between invocation and response. Requires a global clock or consensus. (e.g., Spanner, CockroachDB).
- **Sequential Consistency:** Operations appear to take place in some total order, and the operations of each individual process appear in the order specified by its program. (Relaxation of real-time constraint).

## Weak / Eventual Models
- **Eventual Consistency:** If no new updates are made to a given data item, eventually all accesses to that item will return the last updated value. Offers no safety guarantees in the interim. (e.g., Dynamo, Cassandra).
- **Causal Consistency:** Operations that are causally related must be seen in the same order by all nodes. Operations that are concurrent can be seen in different orders.

## Common LLM Mistakes to Avoid
- Do not state that Cassandra is strictly "Eventually Consistent" without nuance; it offers tunable consistency (e.g., `QUORUM` reads/writes).
- Do not confuse CAP's consistency with ACID's consistency.
- Remember the PACELC extension: Even when the system is running normally (E), you must choose between Latency (L) and Consistency (C).