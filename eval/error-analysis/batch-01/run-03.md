# Run 03

- **assistant_message_id:** `f57cbcfe-702f-423f-9ad1-33abac760254`
- **conversation_id:** `e46bde5e-2f1c-6488-fbeb-5bd10319c943`
- **created_at:** 2026-07-09T08:55:10.661136+00:00

## Input (user query)

> Summarize WiscKey: Separating Keys from Values in SSD-conscious Storage

## Retrieved context (from `messages.sources`)

**[1] Wisckey** (page 0)

```
[Paper: Wisckey] [Section: 3 WiscKey]
To realize an SSD-optimized key-value store, WiscKey includes four critical ideas. First, WiscKey separates keys from values, keeping only keys in the LSM-tree and the values in a separate log file. Second, to deal with unsorted values (which necessitate random access during range queries), WiscKey uses the parallel random-read characteristic of SSD devices. Third, WiscKey utilizes unique crash-consistency and garbagecollection techniques to efficiently manage the value log. Finally, WiscKey optimizes performance by removing the LSM-tree log without sacrificing consistency, thus reducing system-call overhead from small writes.
```

**[2] Wisckey** (page 0)

```
[Paper: Wisckey] [Section: 1 Introduction]
In this paper, we present WiscKey, an SSD-conscious persistent key-value store derived from the popular LSMtree implementation, LevelDB. The central idea behind WiscKey is the separation of keys and values [42]; only keys are kept sorted in the LSM-tree, while values are stored separately in a log. In other words, we decouple key sorting and garbage collection in WiscKey while LevelDB bundles them together.
```

**[3] Wisckey** (page 0)

```
[Paper: Wisckey] [Section: 6 Conclusions]
Key-value stores have become a fundamental building block in data-intensive applications. In this paper, we propose WiscKey, a novel LSM-tree-based key-value store that separates keys and values to minimize write and read amplification. The data layout and I/O patterns of WiscKey are highly optimized for SSD devices. Our results show that WiscKey can significantly improve performance for most workloads. Our hope is that key-value separation and various optimization techniques in WiscKey will inspire the future generation of high-performance key-value stores.
```

**[4] Wisckey** (page 0)

```
[Paper: Wisckey] [Section: 5 Related Work]
Much work has gone into optimizing the original LSM-tree key-value store [43]. bLSM [49] presents a new merge scheduler to bound write latency, thus maintaining a steady write throughput, and also uses bloom filters to improve performance. VT-tree [50] avoids sorting any previously sorted key-value pairs during compaction, by using a layer of indirection. WiscKey instead directly separates values from keys, significantly reducing write amplification regardless of the key distribution in the workload. LOCS [53] exposes internal flash channels to the LSM-tree key-value store, which can exploit the abundant parallelism for a more efficient compaction. Atlas [32] is a distributed key-value store based on ARM processors and erasure coding, and stores keys and values on different hard drives. WiscKey is a standalone key-value store, where the separation between keys and values is highly optimized for SSD devices to achieve significant performance gains. LSM-trie [54] uses a trie structure to organize keys, and proposes a more efficient compaction based on the trie; however, this design sacrifices LSM-tree features such as efficient support for range queries. RocksDB, described previously, still exhibits high write amplification due to its design being fundamentally similar to LevelDB; RocksDB's optimizations are orthogonal to WiscKey's design.
```

**[5] Wisckey** (page 0)

```
[Paper: Wisckey] [Section: Abstract]
We present WiscKey, a persistent LSM-tree-based key-value store with a performance-oriented data layout that separates keys from values to minimize I/O amplification. The design of WiscKey is highly SSD optimized, leveraging both the sequential and random performance characteristics of the device.
```

## Final output

**main:**

<h3>WiscKey: Separating Keys from Values in SSD-conscious Storage</h3>
<p>WiscKey is an SSD-optimized, persistent key-value store that fundamentally improves upon LSM-tree implementations like LevelDB by separating keys from values, storing only keys in the LSM-tree and values in a separate log file.</p>

<p>The central idea behind WiscKey is to decouple key sorting and garbage collection, which are bundled together in traditional LSM-tree designs. This separation is crucial for minimizing write and read amplification, making WiscKey highly efficient for Solid State Drives (SSDs) by leveraging their sequential and random performance characteristics.</p>

<h4>Core Design Principles</h4>
<p>WiscKey incorporates four critical ideas to achieve its SSD-optimized performance:</p>
<ol>
    <li><strong>Key-Value Separation:</strong> Only keys are stored in the LSM-tree, while their corresponding values reside in a separate log file.</li>
    <li><strong>Parallel Random Reads:</strong> It leverages the parallel random-read capabilities of SSDs to efficiently access unsorted values during operations like range queries.</li>
    <li><strong>Unique Crash-Consistency and Garbage Collection:</strong> WiscKey employs specialized techniques for crash consistency and garbage collection to manage the value log efficiently.</li>
    <li><strong>LSM-tree Log Removal:</strong> It removes the traditional LSM-tree log, reducing system-call overhead from small writes without sacrificing consistency.</li>
</ol>

<h4>Benefits and Impact</h4>
<p>By separating keys and values, WiscKey significantly reduces write amplification, regardless of the key distribution in the workload. This design, coupled with its SSD-conscious optimizations, leads to substantial performance improvements for most workloads compared to traditional LSM-tree stores.</p>

<blockquote>
    <p>The data layout and I/O patterns of WiscKey are highly optimized for SSD devices, leading to significant performance improvements for most workloads.</p>
</blockquote>

**other fields:**
```json
{
  "tabs": [
    {
      "title": "Key-Value Separation Diagram",
      "content": "<h3>WiscKey's Key-Value Separation</h3>\n<svg viewBox='0 0 640 360' width='100%'>\n    <!-- Colors for dark UI -->\n    <defs>\n        <linearGradient id=\"lsmGradient\" x1=\"0%\" y1=\"0%\" x2=\"100%\" y2=\"0%\">\n            <stop offset=\"0%\" style=\"stop-color:#4CAF50;stop-opacity:1\" />\n            <stop offset=\"100%\" style=\"stop-color:#8BC34A;stop-opacity:1\" />\n        </linearGradient>\n        <linearGradient id=\"valueLogGradient\" x1=\"0%\" y1=\"0%\" x2=\"100%\" y2=\"0%\">\n            <stop offset=\"0%\" style=\"stop-color:#2196F3;stop-opacity:1\" />\n            <stop offset=\"100%\" style=\"stop-color:#03A9F4;stop-opacity:1\" />\n        </linearGradient>\n        <marker id=\"arrowhead\" markerWidth=\"10\" markerHeight=\"7\" refX=\"0\" refY=\"3.5\" orient=\"auto\">\n            <polygon points=\"0 0, 10 3.5, 0 7\" fill=\"#BBBBBB\" />\n        </marker>\n    </defs>\n\n    <!-- LSM-tree (Keys) -->\n    <rect x=\"50\" y=\"80\" width=\"250\" height=\"180\" rx=\"10\" ry=\"10\" fill=\"url(#lsmGradient)\" stroke=\"#388E3C\" stroke-width=\"2\"/>\n    <text x=\"175\" y=\"50\" font-family=\"Arial\" font-size=\"20\" fill=\"#E0E0E0\" text-anchor=\"middle\">LSM-tree (Sorted Keys)</text>\n    <text x=\"175\" y=\"110\" font-family=\"Arial\" font-size=\"16\" fill=\"#FFFFFF\" text-anchor=\"middle\">Key1 -> Value_Ptr_A</text>\n    <text x=\"175\" y=\"140\" font-family=\"Arial\" font-size=\"16\" fill=\"#FFFFFF\" text-anchor=\"middle\">Key2 -> Value_Ptr_B</text>\n    <text x=\"175\" y=\"170\" font-family=\"Arial\" font-size=\"16\" fill=\"#FFFFFF\" text-anchor=\"middle\">Key3 -> Value_Ptr_C</text>\n    <text x=\"175\" y=\"200\" font-family=\"Arial\" font-size=\"16\" fill=\"#FFFFFF\" text-anchor=\"middle\">...</text>\n    <text x=\"175\" y=\"230\" font-family=\"Arial\" font-size=\"16\" fill=\"#FFFFFF\" text-anchor=\"middle\">KeyN -> Value_Ptr_X</text>\n\n    <!-- Value Log (Unsorted Values) -->\n    <rect x=\"340\" y=\"80\" width=\"250\" height=\"180\" rx=\"10\" ry=\"10\" fill=\"url(#valueLogGradient)\" stroke=\"#1976D2\" stroke-width=\"2\"/>\n    <text x=\"465\" y=\"50\" font-family=\"Arial\" font-size=\"20\" fill=\"#E0E0E0\" text-anchor=\"middle\">Value Log (Unsorted Values)</text>\n    <text x=\"465\" y=\"110\" font-family=\"Arial\" font-size=\"16\" fill=\"#FFFFFF\" text-anchor=\"middle\">Value_C (at Ptr_C)</text>\n    <text x=\"465\" y=\"140\" font-family=\"Arial\" font-size=\"16\" fill=\"#FFFFFF\" text-anchor=\"middle\">Value_A (at Ptr_A)</text>\n    <text x=\"465\" y=\"170\" font-family=\"Arial\" font-size=\"16\" fill=\"#FFFFFF\" text-anchor=\"middle\">Value_X (at Ptr_X)</text>\n    <text x=\"465\" y=\"200\" font-family=\"Arial\" font-size=\"16\" fill=\"#FFFFFF\" text-anchor=\"middle\">...</text>\n    <text x=\"465\" y=\"230\" font-family=\"Arial\" font-size=\"16\" fill=\"#FFFFFF\" text-anchor=\"middle\">Value_B (at Ptr_B)</text>\n\n    <!-- Arrows -->\n    <path d=\"M300 110 H335\" stroke=\"#BBBBBB\" stroke-width=\"2\" marker-end=\"url(#arrowhead)\" />\n    <path d=\"M300 140 H335\" stroke=\"#BBBBBB\" stroke-width=\"2\" marker-end=\"url(#arrowhead)\" />\n    <path d=\"M300 170 H335\" stroke=\"#BBBBBB\" stroke-width=\"2\" marker-end=\"url(#arrowhead)\" />\n    <path d=\"M300 230 H335\" stroke=\"#BBBBBB\" stroke-width=\"2\" marker-end=\"url(#arrowhead)\" />\n\n    <text x=\"320\" y=\"290\" font-family=\"Arial\" font-size=\"18\" fill=\"#E0E0E0\" text-anchor=\"middle\">Value Pointers</text>\n    <path d=\"M320 270 L320 285\" stroke=\"#BBBBBB\" stroke-width=\"2\" marker-end=\"url(#arrowhead)\" />\n</svg>\n<p>This diagram illustrates WiscKey's fundamental separation: the LSM-tree maintains sorted keys, each pointing to its corresponding value stored in an append-only, unsorted value log. This design allows the LSM-tree to remain small and efficient, while values are written sequentially to the log, optimizing for SSD characteristics.</p>"
    },
    {
      "title": "Comparison with LevelDB/RocksDB",
      "content": "<h3>WiscKey vs. Traditional LSM-tree Stores (e.g., LevelDB, RocksDB)</h3>\n<p>WiscKey's design is a direct evolution from LSM-tree implementations like LevelDB, addressing their limitations, particularly concerning SSD performance.</p>\n\n<table>\n    <thead>\n        <tr>\n            <th>Feature</th>\n            <th>Traditional LSM-tree (LevelDB/RocksDB)</th>\n            <th>WiscKey</th>\n        </tr>\n    </thead>\n    <tbody>\n        <tr>\n            <td><strong>Key-Value Storage</strong></td>\n            <td>Keys and values are bundled together and stored within the LSM-tree structure.</td>\n            <td>Keys are stored in the LSM-tree; values are stored separately in an append-only log file.</td>\n        </tr>\n        <tr>\n            <td><strong>Write Amplification</strong></td>\n            <td>High, as entire key-value pairs are rewritten during compaction, especially for large values.</td>\n            <td>Significantly reduced, as only keys are rewritten in the LSM-tree; values are written once sequentially to the log.</td>\n        </tr>\n        <tr>\n            <td><strong>Read Amplification</strong></td>\n            <td>Can be high due to multiple lookups across LSM-tree levels.</td>\n            <td>Minimized; a key lookup in the LSM-tree provides a direct pointer to the value, which is then read in a single I/O.</td>\n        </tr>\n        <tr>\n            <td><strong>Garbage Collection</strong></td>\n            <td>Bundled with LSM-tree compaction, leading to rewriting live data.</td>\n            <td>Decoupled from key sorting; uses unique techniques to manage the value log efficiently.</td>\n        </tr>\n        <tr>\n            <td><strong>SSD Optimization</strong></td>\n            <td>Not inherently optimized; can lead to excessive random writes and erasures.</td>\n            <td>Highly optimized for SSDs, leveraging sequential writes for values and parallel random reads for value retrieval.</td>\n        </tr>\n        <tr>\n            <td><strong>LSM-tree Log</strong></td>\n            <td>Typically uses a write-ahead log for consistency.</td>\n            <td>Removes the LSM-tree log to reduce system-call overhead.</td>\n        </tr>\n    </tbody>\n</table>\n<p>RocksDB, while offering optimizations, still exhibits high write amplification because its fundamental design is similar to LevelDB, making its optimizations orthogonal to WiscKey's core design.</p>"
    },
    {
      "title": "Related Work Context",
      "content": "<h3>WiscKey in the Context of Related Work</h3>\n<p>WiscKey builds upon and differentiates itself from various efforts to optimize LSM-tree key-value stores:</p>\n<ul>\n    <li><strong>bLSM:</strong> Focuses on a new merge scheduler to bound write latency and uses bloom filters. WiscKey's approach is distinct by separating keys and values.</li>\n    <li><strong>VT-tree:</strong> Aims to avoid sorting previously sorted key-value pairs using indirection. WiscKey, instead, directly separates values from keys to reduce write amplification.</li>\n    <li><strong>LOCS:</strong> Exploits internal flash channels for more efficient compaction by exposing them to the LSM-tree. WiscKey's optimization is at a higher architectural level.</li>\n    <li><strong>Atlas:</strong> A distributed key-value store that stores keys and values on different hard drives. WiscKey is a standalone store, with its separation highly optimized for SSDs.</li>\n    <li><strong>LSM-trie:</strong> Uses a trie structure for keys and proposes efficient compaction, but sacrifices LSM-tree features like efficient range query support. WiscKey maintains LSM-tree features while optimizing for SSDs.</li>\n</ul>\n<p>WiscKey's key-value separation is a novel approach that directly tackles I/O amplification, offering a distinct advantage over these other optimization techniques.</p>"
    }
  ]
}
```

## Human note

_(fill in: what, if anything, went wrong here — no categories yet)_

note:
