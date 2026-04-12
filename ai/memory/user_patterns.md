# User Patterns

This document characterizes the primary user personas interacting with the Database Research RAG system and their typical query patterns. AI agents should use this to tailor system responses and UI/UX design.

## User Personas

1. **Academic Researchers & Students:**
   - **Goal:** Understand theoretical foundations, compare algorithms, trace the evolution of concepts.
   - **Query Style:** Conceptual, comparative, deep.
   - **Example:** "How does the leader election in Raft differ from multi-Paxos?"
   - **Needs:** High fidelity to original text, exact quotes, page numbers, links to original PDFs.

2. **Database Engineers & Architects:**
   - **Goal:** Solve practical system design problems, choose the right technology for a use case, understand failure modes.
   - **Query Style:** Practical, tradeoff-focused, architectural.
   - **Example:** "What are the trade-offs between LSM-trees and B-trees for write-heavy workloads as described in the WiscKey paper?"
   - **Needs:** Clear summaries of tradeoffs, architectural diagrams, performance characteristics.

3. **Software Developers (General):**
   - **Goal:** Learn database concepts, understand CAP theorem, figure out why their database is behaving a certain way.
   - **Query Style:** Definitional, troubleshooting-oriented.
   - **Example:** "What does eventual consistency mean in DynamoDB?"
   - **Needs:** Simple explanations backed by authoritative sources, avoiding overly dense academic jargon unless necessary.

## Common Interaction Patterns
- **Iterative Questioning:** Users rarely ask one question. They ask a broad question ("Explain Spanner's TrueTime"), followed by a specific drill-down ("How does it handle clock skew?"). The RAG system must maintain conversational memory and contextual context.
- **Verification:** Users often ask for proof. They want to see the exact paragraph where a claim was made. The UI must support highlighting the retrieved chunk in the context of the original PDF.
- **Comparative Analysis:** A massive percentage of queries involve "X vs Y" (e.g., Cassandra vs Bigtable). The retrieval strategy must ensure it pulls chunks describing *both* systems to provide a balanced answer.