# Run 08

- **assistant_message_id:** `2244fbac-2537-4417-8e51-63121a14c72f`
- **conversation_id:** `f7a3c57b-2279-b6ee-8146-3bc4e52a35c5`
- **created_at:** 2026-07-09T08:54:04.057032+00:00

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

<h3>WiscKey: An SSD-Optimized Key-Value Store with Key-Value Separation</h3>
<p>WiscKey is an SSD-conscious persistent key-value store that fundamentally improves upon LSM-tree implementations like LevelDB by separating keys from values, storing only keys in the LSM-tree and values in a separate log file.</p>

<p>The central idea behind WiscKey is to decouple key sorting and garbage collection, which are bundled together in traditional LSM-tree designs. This separation is highly optimized for SSD devices, leveraging their parallel random-read capabilities and sequential write performance to minimize I/O amplification and significantly improve performance for most workloads.</p>

<h4>Core Design Principles</h4>
<p>WiscKey incorporates four critical ideas to achieve its SSD-optimized performance:</p>
<ol>
    <li><strong>Key-Value Separation:</strong> Keys are stored in the LSM-tree, while values reside in a separate log file. This reduces the amount of data that needs to be sorted and moved during compaction.</li>
    <li><strong>Parallel Random Reads for Values:</strong> Although values in the log file are unsorted, WiscKey exploits the parallel random-read characteristic of SSDs to efficiently access them, particularly during range queries.</li>
    <li><strong>Unique Crash-Consistency and Garbage Collection:</strong> WiscKey employs specialized techniques for crash consistency and garbage collection to efficiently manage the separate value log.</li>
    <li><strong>LSM-tree Log Removal:</strong> It removes the LSM-tree log without sacrificing consistency, which reduces system-call overhead from small writes and further optimizes performance.</li>
</ol>

<h4>SSD Optimization</h4>
<p>WiscKey's design is specifically tailored for SSDs, leveraging both their sequential and random performance characteristics. By separating keys and values, it significantly reduces write and read amplification, regardless of the key distribution in the workload.</p>

<blockquote>
    <p>The central idea behind WiscKey is the separation of keys and values; only keys are kept sorted in the LSM-tree, while values are stored separately in a log. In other words, we decouple key sorting and garbage collection in WiscKey while LevelDB bundles them together.</p>
</blockquote>

**other fields:**
```json
{
  "tabs": [
    {
      "title": "Key-Value Separation Diagram",
      "content": "<svg viewBox='0 0 640 360' width='100%'>\n    <!-- Colors for dark UI -->\n    <style>\n        .node-key { fill: #64B5F6; stroke: #2196F3; stroke-width: 2; }\n        .node-value { fill: #FFB74D; stroke: #FF9800; stroke-width: 2; }\n        .node-lsm { fill: #81C784; stroke: #4CAF50; stroke-width: 2; }\n        .node-log { fill: #E57373; stroke: #F44336; stroke-width: 2; }\n        .text-label { fill: #FFFFFF; font-family: sans-serif; font-size: 14px; text-anchor: middle; }\n        .arrow { stroke: #FFFFFF; stroke-width: 2; marker-end: url(#arrowhead); }\n        .concept-box { fill: #424242; stroke: #757575; stroke-width: 1; }\n        .concept-text { fill: #FFFFFF; font-family: sans-serif; font-size: 16px; text-anchor: middle; }\n    </style>\n\n    <defs>\n        <marker id=\"arrowhead\" markerWidth=\"10\" markerHeight=\"7\" refX=\"0\" refY=\"3.5\" orient=\"auto\">\n            <polygon points=\"0 0, 10 3.5, 0 7\" fill=\"#FFFFFF\" />\n        </marker>\n    </defs>\n\n    <!-- Title -->\n    <text x=\"320\" y=\"30\" class=\"concept-text\" font-size=\"20px\">WiscKey: Key-Value Separation</text>\n\n    <!-- LSM-tree (Keys) -->\n    <rect x=\"80\" y=\"100\" width=\"200\" height=\"150\" rx=\"10\" ry=\"10\" class=\"node-lsm\" />\n    <text x=\"180\" y=\"125\" class=\"text-label\" font-size=\"18px\">LSM-tree</text>\n    <text x=\"180\" y=\"155\" class=\"text-label\">Sorted Keys</text>\n    <text x=\"180\" y=\"185\" class=\"text-label\">(Key, Value_Pointer)</text>\n    <text x=\"180\" y=\"215\" class=\"text-label\">Optimized for Writes</text>\n\n    <!-- Value Log (Values) -->\n    <rect x=\"360\" y=\"100\" width=\"200\" height=\"150\" rx=\"10\" ry=\"10\" class=\"node-log\" />\n    <text x=\"460\" y=\"125\" class=\"text-label\" font-size=\"18px\">Value Log</text>\n    <text x=\"460\" y=\"155\" class=\"text-label\">Unsorted Values</text>\n    <text x=\"460\" y=\"185\" class=\"text-label\">(Value Data)</text>\n    <text x=\"460\" y=\"215\" class=\"text-label\">Optimized for Reads (SSD)</text>\n\n    <!-- Arrows -->\n    <path d=\"M280 175 H360\" class=\"arrow\" />\n    <text x=\"320\" y=\"165\" class=\"text-label\" font-size=\"12px\">Value Pointer</text>\n    <text x=\"320\" y=\"190\" class=\"text-label\" font-size=\"12px\">References</text>\n\n    <!-- SSD Context -->\n    <rect x=\"50\" y=\"280\" width=\"540\" height=\"60\" rx=\"10\" ry=\"10\" class=\"concept-box\" />\n    <text x=\"320\" y=\"315\" class=\"concept-text\">Highly Optimized for SSD Devices (Sequential Writes, Parallel Random Reads)</text>\n</svg>"
    },
    {
      "title": "Comparison with LevelDB/RocksDB",
      "content": "<h3>WiscKey vs. LevelDB/RocksDB</h3>\n<p>WiscKey's fundamental departure from traditional LSM-tree designs like LevelDB and RocksDB lies in its key-value separation. This leads to significant differences in how data is managed and optimized.</p>\n\n<table>\n    <thead>\n        <tr>\n            <th>Feature</th>\n            <th>LevelDB/RocksDB (Traditional LSM-tree)</th>\n            <th>WiscKey (Key-Value Separated)</th>\n        </tr>\n    </thead>\n    <tbody>\n        <tr>\n            <td><strong>Data Layout</strong></td>\n            <td>Keys and values are stored together in the LSM-tree.</td>\n            <td>Keys (with value pointers) are in the LSM-tree; values are in a separate log file.</td>\n        </tr>\n        <tr>\n            <td><strong>Write Amplification</strong></td>\n            <td>High, as entire key-value pairs are rewritten during compaction.</td>\n            <td>Significantly reduced, as only keys (and small value pointers) are rewritten in the LSM-tree.</td>\n        </tr>\n        <tr>\n            <td><strong>Read Amplification</strong></td>\n            <td>Can be high due to multiple lookups across LSM-tree levels.</td>\n            <td>Minimized; a single LSM-tree lookup for the key, then a direct read from the value log.</td>\n        </tr>\n        <tr>\n            <td><strong>Garbage Collection</strong></td>\n            <td>Bundled with key sorting during compaction.</td>\n            <td>Decoupled from key sorting; managed separately for the value log.</td>\n        </tr>\n        <tr>\n            <td><strong>SSD Optimization</strong></td>\n            <td>Not inherently optimized for SSD characteristics; can lead to excessive writes.</td>\n            <td>Highly optimized for SSDs, leveraging sequential writes for the value log and parallel random reads for value retrieval.</td>\n        </tr>\n        <tr>\n            <td><strong>LSM-tree Log</strong></td>\n            <td>Typically uses a write-ahead log for consistency.</td>\n            <td>Removes the LSM-tree log to reduce system-call overhead.</td>\n        </tr>\n    </tbody>\n</table>"
    },
    {
      "title": "Related Work Context",
      "content": "<h3>WiscKey in the Context of Related Work</h3>\n<p>WiscKey builds upon and differentiates itself from other efforts to optimize LSM-tree key-value stores:</p>\n<ul>\n    <li><strong>bLSM:</strong> Focuses on a new merge scheduler to bound write latency and uses Bloom filters for performance. WiscKey's approach is orthogonal, addressing write amplification through data layout.</li>\n    <li><strong>VT-tree:</strong> Aims to avoid sorting previously sorted key-value pairs during compaction using indirection. WiscKey directly separates values, offering a different strategy to reduce write amplification.</li>\n    <li><strong>LOCS:</strong> Exploits internal flash channels for more efficient compaction by exposing them to the LSM-tree. WiscKey's optimization is at the logical data layout level, independent of flash channel exposure.</li>\n    <li><strong>Atlas:</strong> A distributed key-value store that stores keys and values on different hard drives. WiscKey is a standalone key-value store, with its separation highly optimized for SSDs.</li>\n    <li><strong>LSM-trie:</strong> Uses a trie structure for keys and proposes efficient compaction, but sacrifices LSM-tree features like efficient range query support. WiscKey maintains LSM-tree features while optimizing I/O.</li>\n    <li><strong>RocksDB:</strong> While RocksDB offers many optimizations, its design is fundamentally similar to LevelDB, meaning it still exhibits high write amplification. WiscKey's design is distinct and complementary to RocksDB's optimizations.</li>\n</ul>\n<p>WiscKey's key-value separation is a novel approach that directly tackles I/O amplification, inspiring future generations of high-performance key-value stores.</p>"
    }
  ]
}
```

## Human note

_(fill in: what, if anything, went wrong here — no categories yet)_

note:
