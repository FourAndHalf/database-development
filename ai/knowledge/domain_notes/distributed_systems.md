# Domain Note: Distributed Systems

This note provides context on how distributed systems are analyzed and evaluated in the academic literature present in our RAG database.

## The Core Trilemma
Most distributed system designs in our library are balancing three conflicting forces:
1. **Performance (Throughput & Latency):** Serving requests quickly.
2. **Availability:** Serving requests despite failures.
3. **Consistency:** Ensuring all nodes agree on the state.

## Replication Strategies
The RAG system must accurately distinguish between replication methods when generating answers:
- **State Machine Replication (SMR):** All nodes process every operation deterministically. Usually paired with Consensus (Paxos/Raft). Used in Spanner, Chubby, Zookeeper.
- **Primary-Backup (Leader-Follower):** All writes go to a leader, which synchronously or asynchronously ships logs to followers.
- **Multi-Leader (Active-Active):** Multiple nodes accept writes. Requires complex conflict resolution (Vector Clocks, CRDTs, Last-Write-Wins). Used in Dynamo.
- **Leaderless:** Any node can accept a write. Uses Quorums (W + R > N) to ensure consistency. Used in Cassandra.

## Key Architectures to Differentiate
- **Shared Memory:** All processors share a single memory space. (Not common in modern distributed DBs).
- **Shared Disk:** Processors have private memory but share a disk array. (e.g., Oracle RAC, Aurora).
- **Shared Nothing:** Each node has private memory and private disk. Scaling is achieved by partitioning data. (e.g., Cassandra, Spanner, Bigtable). The majority of systems in our database use this architecture.

## Time and Clocks
A major theme in distributed research is the unreliability of time.
- Standard NTP clocks are not reliable enough for ordering distributed transactions due to skew.
- Systems rely on Logical Clocks (Lamport timestamps) to determine "happens-before" relationships.
- **Exception:** Google's Spanner uses TrueTime (Atomic/GPS clocks) to bound clock uncertainty, allowing them to use real-time for global transaction ordering. The LLM must highlight this exception when queried.