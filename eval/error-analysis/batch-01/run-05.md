# Run 05

- **assistant_message_id:** `afd32125-fb10-480c-b814-f6ae5f6941fe`
- **conversation_id:** `f7a3c57b-2279-b6ee-8146-3bc4e52a35c5`
- **created_at:** 2026-07-09T01:22:30.985675+00:00

## Input (user query)

> Provide a comprehensive comparison of storage engines: B-Trees vs. LSM-Trees. Include their write-amplification characteristics, read latencies, and optimal use cases in modern databases.

## Retrieved context (from `messages.sources`)

**[1] Wisckey** (page 0)

```
[Paper: Wisckey] [Section: 1 Introduction]
Various distributed and local stores built on LSM-trees are widely deployed in largescale production environments, such as BigTable [16] and LevelDB [48] at Google, Cassandra [33], HBase [29] and RocksDB [25] at Facebook, PNUTS [20] at Yahoo!, and Riak [4] at Basho. The main advantage of LSMtrees over other indexing structures (such as B-trees) is that they maintain sequential access patterns for writes. Small updates on B-trees may involve many random writes, and are hence not efficient on either solid-state storage devices or hard-disk drives.
```

**[2] Wisckey** (page 0)

```
[Paper: Wisckey] [Section: 2.3 Write and Read Amplification]
It should be noted that the high write and read amplifications are a justified tradeoff for hard drives. As an example, for a given hard drive with a 10-ms seek latency and a 100-MB/s throughput, the approximate time required to access a random 1K of data is 10 ms, while that for the next sequential block is about 10 µ s - the ratio between random and sequential latency is 1000:1. Hence, compared to alternative data structures such as B-Trees that require random write accesses, a sequential-writeonly scheme with write amplification less than 1000 will be faster on a hard drive [43, 49]. On the other hand, the read amplification for LSM-trees is still comparable to B-Trees. For example, considering a B-Tree with a height of five and a block size of 4 KB, a random lookup for a 1-KB key-value pair would require accessing six blocks, resulting in a read amplification of 24.
```

**[3] Wisckey** (page 0)

```
[Paper: Wisckey] [Section: 2.1 Log-Structured Merge-Tree]
inserts and deletes [43]. It defers and batches data writes into large chunks to use the high sequential bandwidth of hard drives. Since random writes are nearly two orders of magnitude slower than sequential writes on hard drives, LSM-trees provide better write performance than traditional B-trees, which require random accesses.
```

**[4] Wisckey** (page 0)

```
[Paper: Wisckey] [Section: 2.1 Log-Structured Merge-Tree]
To serve a lookup operation, LSM-trees may need to search multiple components. Note that C 0 contains the freshest data, followed by C 1 , and so on. Therefore, to retrieve a key-value pair, the LSM-tree searches components starting from C 0 in a cascading fashion until it locates the desired data in the smallest component C i . Compared with B-trees, LSM-trees may need multiple reads for a point lookup. Hence, LSM-trees are most useful when inserts are more common than lookups [43].
```

**[5] Wisckey** (page 0)

```
[Paper: Wisckey] [Section: 5 Related Work]
Much work has gone into optimizing the original LSM-tree key-value store [43]. bLSM [49] presents a new merge scheduler to bound write latency, thus maintaining a steady write throughput, and also uses bloom filters to improve performance. VT-tree [50] avoids sorting any previously sorted key-value pairs during compaction, by using a layer of indirection. WiscKey instead directly separates values from keys, significantly reducing write amplification regardless of the key distribution in the workload. LOCS [53] exposes internal flash channels to the LSM-tree key-value store, which can exploit the abundant parallelism for a more efficient compaction. Atlas [32] is a distributed key-value store based on ARM processors and erasure coding, and stores keys and values on different hard drives. WiscKey is a standalone key-value store, where the separation between keys and values is highly optimized for SSD devices to achieve significant performance gains. LSM-trie [54] uses a trie structure to organize keys, and proposes a more efficient compaction based on the trie; however, this design sacrifices LSM-tree features such as efficient support for range queries. RocksDB, described previously, still exhibits high write amplification due to its design being fundamentally similar to LevelDB; RocksDB's optimizations are orthogonal to WiscKey's design.
```

## Final output

**main:**

<h3>B-Trees vs. LSM-Trees: A Comprehensive Comparison</h3>
<p>B-Trees excel in scenarios requiring low read latency and efficient random access, while LSM-Trees are optimized for high write throughput through sequential writes, making a trade-off with potentially higher read amplification.</p>

<p>The choice between B-Trees and LSM-Trees hinges on the dominant workload pattern and the underlying storage characteristics, particularly the cost of random versus sequential I/O.</p>

<h4>Comparison Table: B-Trees vs. LSM-Trees</h4>
<table>
    <thead>
        <tr>
            <th>Feature</th>
            <th>B-Trees</th>
            <th>LSM-Trees</th>
        </tr>
    </thead>
    <tbody>
        <tr>
            <td><strong>Write Pattern</strong></td>
            <td>Random writes (small updates involve many random writes)</td>
            <td>Sequential writes (batches data into large chunks)</td>
        </tr>
        <tr>
            <td><strong>Write Amplification</strong></td>
            <td>Lower (but involves random writes, inefficient on HDDs/SSDs)</td>
            <td>Higher (justified tradeoff for sequential writes on HDDs, can be significant)</td>
        </tr>
        <tr>
            <td><strong>Read Latency (Point Lookup)</strong></td>
            <td>Generally lower (e.g., 6 block accesses for a 5-height B-Tree)</td>
            <td>Potentially higher (may need to search multiple components in cascading fashion)</td>
        </tr>
        <tr>
            <td><strong>Read Amplification</strong></td>
            <td>Comparable to LSM-Trees (e.g., 24 for a 1KB KV pair in a 5-height B-Tree)</td>
            <td>Comparable to B-Trees</td>
        </tr>
        <tr>
            <td><strong>Optimal Use Cases</strong></td>
            <td>Workloads with frequent random lookups and updates, where read latency is critical.</td>
            <td>Write-heavy workloads, where inserts are more common than lookups, leveraging high sequential bandwidth.</td>
        </tr>
        <tr>
            <td><strong>Storage Efficiency</strong></td>
            <td>Efficient for random access.</td>
            <td>Optimized for sequential access on hard drives; can be further optimized for SSDs (e.g., WiscKey).</td>
        </tr>
        <tr>
            <td><strong>Examples</strong></td>
            <td>Traditional relational databases.</td>
            <td>BigTable, LevelDB, Cassandra, HBase, RocksDB, PNUTS, Riak.</td>
        </tr>
    </tbody>
</table>

<h4>Write Amplification Characteristics</h4>
<p><strong>B-Trees:</strong> While B-Trees might appear to have lower "write amplification" in terms of the number of bytes written per logical write, their fundamental issue lies in their access pattern. Small updates on B-trees often involve many *random writes*. This random access pattern is highly inefficient on both solid-state drives (SSDs) and hard-disk drives (HDDs).</p>

<p><strong>LSM-Trees:</strong> LSM-Trees are designed to maintain sequential access patterns for writes. They defer and batch data writes into large chunks, leveraging the high sequential bandwidth of hard drives. This sequential-write-only scheme comes with a trade-off: high write amplification. However, this is considered a justified trade-off for hard drives because random writes are nearly two orders of magnitude slower than sequential writes. For instance, if the write amplification is less than 1000, an LSM-tree can still be faster than a B-tree on a hard drive due to the 1000:1 ratio between random and sequential latency.</p>

<blockquote>
    <p>The main advantage of LSM-trees over other indexing structures (such as B-trees) is that they maintain sequential access patterns for writes. Small updates on B-trees may involve many random writes, and are hence not efficient on either solid-state storage devices or hard-disk drives.</p>
</blockquote>

<h4>Read Latencies</h4>
<p><strong>B-Trees:</strong> B-Trees generally offer lower read latency for point lookups. For example, a B-Tree with a height of five and a block size of 4 KB would require accessing six blocks for a random lookup of a 1-KB key-value pair, resulting in a read amplification of 24. The read path is typically direct, following the tree structure to the desired data block.</p>

<p><strong>LSM-Trees:</strong> LSM-Trees may exhibit higher read latencies for point lookups because they might need to search multiple components (e.g., C0, C1, etc.) in a cascading fashion until the desired data is located. The freshest data is in C0, followed by C1, and so on. While their read amplification is still comparable to B-Trees, the need to check multiple sorted components can increase lookup time.</p>

<h4>Optimal Use Cases</h4>
<p><strong>B-Trees:</strong> B-Trees are best suited for workloads where random lookups and updates are frequent, and low read latency is a primary concern. They are the traditional choice for relational databases and scenarios requiring strong transactional guarantees and efficient random access.</p>

<p><strong>LSM-Trees:</strong> LSM-Trees are most useful when inserts (and deletes) are more common than lookups. Their strength lies in handling write-heavy workloads by batching and performing sequential writes, which is highly efficient on hard drives and can be optimized for SSDs. They are widely deployed in large-scale production environments like BigTable, Cassandra, HBase, and RocksDB.</p>

**other fields:**
```json
{
  "tabs": [
    {
      "title": "Write Amplification Tradeoff",
      "content": "<h3>Write Amplification Tradeoff</h3>\n<p>The core difference in write performance stems from how each structure handles disk I/O.</p>\n<svg viewBox='0 0 640 360' width='100%'>\n    <rect x='20' y='30' width='280' height='150' rx='10' ry='10' fill='#282c34' stroke='#61afef' stroke-width='2'/>\n    <text x='160' y='60' font-family='sans-serif' font-size='18' fill='#e06c75' text-anchor='middle'>B-Tree Writes</text>\n    <rect x='50' y='80' width='220' height='30' fill='#3e4451' rx='5' ry='5'/>\n    <text x='160' y='100' font-family='sans-serif' font-size='14' fill='#abb2bf' text-anchor='middle'>Small Update</text>\n    <line x1='160' y1='115' x2='160' y2='135' stroke='#c678dd' stroke-width='2' marker-end='url(#arrow)'/>\n    <text x='160' y='155' font-family='sans-serif' font-size='14' fill='#e5c07b' text-anchor='middle'>Many Random Writes</text>\n\n    <rect x='340' y='30' width='280' height='150' rx='10' ry='10' fill='#282c34' stroke='#98c379' stroke-width='2'/>\n    <text x='480' y='60' font-family='sans-serif' font-size='18' fill='#e06c75' text-anchor='middle'>LSM-Tree Writes</text>\n    <rect x='370' y='80' width='220' height='30' fill='#3e4451' rx='5' ry='5'/>\n    <text x='480' y='100' font-family='sans-serif' font-size='14' fill='#abb2bf' text-anchor='middle'>Small Update</text>\n    <line x1='480' y1='115' x2='480' y2='135' stroke='#c678dd' stroke-width='2' marker-end='url(#arrow)'/>\n    <text x='480' y='155' font-family='sans-serif' font-size='14' fill='#98c379' text-anchor='middle'>Batched Sequential Writes</text>\n\n    <line x1='310' y1='200' x2='310' y2='300' stroke='#61afef' stroke-width='2' stroke-dasharray='5,5'/>\n    <text x='320' y='250' font-family='sans-serif' font-size='16' fill='#abb2bf'>Tradeoff</text>\n\n    <rect x='20' y='220' width='280' height='120' rx='10' ry='10' fill='#282c34' stroke='#e5c07b' stroke-width='2'/>\n    <text x='160' y='245' font-family='sans-serif' font-size='16' fill='#e5c07b' text-anchor='middle'>B-Tree Impact</text>\n    <text x='160' y='275' font-family='sans-serif' font-size='14' fill='#abb2bf' text-anchor='middle'>Inefficient on HDDs/SSDs</text>\n    <text x='160' y='295' font-family='sans-serif' font-size='14' fill='#abb2bf' text-anchor='middle'>due to random I/O.</text>\n\n    <rect x='340' y='220' width='280' height='120' rx='10' ry='10' fill='#282c34' stroke='#e5c07b' stroke-width='2'/>\n    <text x='480' y='245' font-family='sans-serif' font-size='16' fill='#e5c07b' text-anchor='middle'>LSM-Tree Impact</text>\n    <text x='480' y='275' font-family='sans-serif' font-size='14' fill='#abb2bf' text-anchor='middle'>Higher Write Amplification,</text>\n    <text x='480' y='295' font-family='sans-serif' font-size='14' fill='#abb2bf' text-anchor='middle'>but faster due to sequential I/O.</text>\n\n    <defs>\n        <marker id='arrow' markerWidth='10' markerHeight='10' refX='5' refY='5' orient='auto' markerUnits='strokeWidth'>\n            <path d='M0,0 L5,5 L0,10 z' fill='#c678dd' />\n        </marker>\n    </defs>\n</svg>\n<p>The critical factor is the performance difference between random and sequential I/O. On a hard drive, the ratio between random and sequential latency can be as high as 1000:1 (e.g., 10 ms seek latency for 1KB random vs. 10 \u00b5s for the next sequential block). This makes LSM-trees' sequential-write approach significantly more efficient for writes, even with higher write amplification, as long as the amplification factor is less than this latency ratio.</p>"
    },
    {
      "title": "LSM-Tree Read Path",
      "content": "<h3>LSM-Tree Read Path</h3>\n<p>To understand LSM-tree read latency, it's important to visualize how a lookup operation proceeds through its components.</p>\n<svg viewBox='0 0 640 360' width='100%'>\n    <rect x='20' y='30' width='100' height='60' rx='5' ry='5' fill='#61afef'/>\n    <text x='70' y='65' font-family='sans-serif' font-size='16' fill='#282c34' text-anchor='middle'>C0 (Memtable)</text>\n    <line x1='120' y1='60' x2='160' y2='60' stroke='#c678dd' stroke-width='2' marker-end='url(#arrow)'/>\n    <text x='130' y='50' font-family='sans-serif' font-size='12' fill='#abb2bf'>Search</text>\n\n    <rect x='180' y='30' width='100' height='60' rx='5' ry='5' fill='#98c379'/>\n    <text x='230' y='65' font-family='sans-serif' font-size='16' fill='#282c34' text-anchor='middle'>C1 (SSTable)</text>\n    <line x1='280' y1='60' x2='320' y2='60' stroke='#c678dd' stroke-width='2' marker-end='url(#arrow)'/>\n    <text x='290' y='50' font-family='sans-serif' font-size='12' fill='#abb2bf'>Search</text>\n\n    <rect x='340' y='30' width='100' height='60' rx='5' ry='5' fill='#e5c07b'/>\n    <text x='390' y='65' font-family='sans-serif' font-size='16' fill='#282c34' text-anchor='middle'>C2 (SSTable)</text>\n    <line x1='440' y1='60' x2='480' y2='60' stroke='#c678dd' stroke-width='2' marker-end='url(#arrow)'/>\n    <text x='450' y='50' font-family='sans-serif' font-size='12' fill='#abb2bf'>Search</text>\n\n    <rect x='500' y='30' width='100' height='60' rx='5' ry='5' fill='#e06c75'/>\n    <text x='550' y='65' font-family='sans-serif' font-size='16' fill='#282c34' text-anchor='middle'>Cn (SSTable)</text>\n\n    <path d='M100 120 C 100 180, 540 180, 540 120' stroke='#abb2bf' stroke-width='2' fill='none' stroke-dasharray='5,5'/>\n    <text x='320' y='160' font-family='sans-serif' font-size='14' fill='#abb2bf' text-anchor='middle'>Cascading Search Order</text>\n\n    <rect x='20' y='200' width='600' height='120' rx='10' ry='10' fill='#282c34' stroke='#c678dd' stroke-width='2'/>\n    <text x='320' y='225' font-family='sans-serif' font-size='18' fill='#e06c75' text-anchor='middle'>Lookup Process</text>\n    <text x='320' y='255' font-family='sans-serif' font-size='14' fill='#abb2bf' text-anchor='middle'>1. Start search from C0 (freshest data).</text>\n    <text x='320' y='275' font-family='sans-serif' font-size='14' fill='#abb2bf' text-anchor='middle'>2. If not found, proceed to C1, then C2, and so on.</text>\n    <text x='320' y='295' font-family='sans-serif' font-size='14' fill='#abb2bf' text-anchor='middle'>3. Stop when key-value pair is located in the smallest component Ci.</text>\n    <text x='320' y='315' font-family='sans-serif' font-size='14' fill='#e5c07b' text-anchor='middle'>Result: May require multiple reads for a single point lookup.</text>\n\n    <defs>\n        <marker id='arrow' markerWidth='10' markerHeight='10' refX='5' refY='5' orient='auto' markerUnits='strokeWidth'>\n            <path d='M0,0 L5,5 L0,10 z' fill='#c678dd' />\n        </marker>\n    </defs>\n</svg>\n<p>This cascading search means that in the worst case, an LSM-tree might have to check every component (from the in-memory memtable to the oldest SSTable on disk) to find a key or confirm its absence. This is why LSM-trees are generally favored when writes are more frequent than reads. Optimizations like Bloom filters are often used to reduce the number of components that need to be checked on disk, thereby improving read performance.</p>"
    },
    {
      "title": "LSM-Tree Optimizations",
      "content": "<h3>LSM-Tree Optimizations</h3>\n<p>Given the widespread adoption of LSM-trees, significant research and development have focused on mitigating their inherent drawbacks, particularly write amplification and read latency.</p>\n<ul>\n    <li><strong>bLSM:</strong> Introduces a new merge scheduler to bound write latency and maintain steady write throughput. It also uses Bloom filters to improve read performance by quickly determining if a key is *not* present in a specific component.</li>\n    <li><strong>VT-tree:</strong> Aims to reduce write amplification by avoiding the re-sorting of already sorted key-value pairs during compaction through a layer of indirection.</li>\n    <li><strong>WiscKey:</strong> Directly separates values from keys, significantly reducing write amplification, especially for SSD devices. This is particularly effective regardless of the key distribution in the workload.</li>\n    <li><strong>LOCS:</strong> Exploits internal flash channels in SSDs to achieve more efficient compaction by leveraging abundant parallelism.</li>\n    <li><strong>LSM-trie:</strong> Uses a trie structure for organizing keys and proposes a more efficient compaction. However, this design sacrifices some LSM-tree features, such as efficient support for range queries.</li>\n    <li><strong>RocksDB:</strong> While fundamentally similar to LevelDB and still exhibiting high write amplification, RocksDB includes various optimizations that are orthogonal to designs like WiscKey.</li>\n</ul>\n<p>These optimizations highlight the continuous effort to balance the write-optimized nature of LSM-trees with improved read performance and reduced resource consumption.</p>"
    }
  ]
}
```

## Human note

_(fill in: what, if anything, went wrong here — no categories yet)_

note:
