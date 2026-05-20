import json
import os
import shutil
import psycopg2
import chromadb
from chromadb.config import Settings

# 1. Load the mapping
with open("paper_mapping.json") as f:
    mapping = json.load(f)

# Define clean filenames
clean_mapping = {}
for old_file, meta in mapping.items():
    if "dynamo" in old_file.lower(): new_file = "Dynamo.pdf"
    elif "spanner" in old_file.lower(): new_file = "Spanner.pdf"
    elif "bigtable" in old_file.lower(): new_file = "Bigtable.pdf"
    elif "cassandra" in old_file.lower(): new_file = "Cassandra.pdf"
    elif "raft" in old_file.lower(): new_file = "Raft.pdf"
    elif "paxos_made_simple" in old_file.lower(): new_file = "Paxos_Made_Simple.pdf"
    elif "paxos_made_practical" in old_file.lower(): new_file = "Paxos_Made_Practical.pdf"
    elif "flexible_paxos" in old_file.lower(): new_file = "Flexible_Paxos.pdf"
    elif "google_file_system" in old_file.lower(): new_file = "GFS.pdf"
    elif "zookeeper" in old_file.lower(): new_file = "ZooKeeper.pdf"
    elif "chubby" in old_file.lower(): new_file = "Chubby.pdf"
    elif "dremel" in old_file.lower(): new_file = "Dremel.pdf"
    elif "wisckey" in old_file.lower(): new_file = "WiscKey.pdf"
    elif "pacelc" in old_file.lower(): new_file = "PACELC.pdf"
    elif "megastore" in old_file.lower(): new_file = "Megastore.pdf"
    elif "f1" in old_file.lower(): new_file = "F1.pdf"
    elif "rocksdb" in old_file.lower(): new_file = "RocksDB.pdf"
    elif "wiredtiger" in old_file.lower(): new_file = "WiredTiger.pdf"
    elif "c_store" in old_file.lower(): new_file = "C-Store.pdf"
    elif "riak" in old_file.lower(): new_file = "Riak.pdf"
    elif "aerospike" in old_file.lower(): new_file = "Aerospike.pdf"
    elif "ycsb" in old_file.lower(): new_file = "YCSB.pdf"
    elif "consistent_hashing" in old_file.lower(): new_file = "Consistent_Hashing.pdf"
    elif "chain_replication" in old_file.lower(): new_file = "Chain_Replication.pdf"
    elif "viewstamped" in old_file.lower(): new_file = "Viewstamped_Replication.pdf"
    else: new_file = meta["title"].replace(" ", "_").replace(":", "").replace("'", "")[:30] + ".pdf"
    
    # Avoid duplicates
    base_name = new_file
    counter = 1
    while any(v["new_file"] == new_file for v in clean_mapping.values()):
        new_file = base_name.replace(".pdf", f"_{counter}.pdf")
        counter += 1
        
    clean_mapping[old_file] = {
        "title": meta["title"],
        "author": meta["author"],
        "new_file": new_file
    }

# 2. Rename physical files
raw_dir = "data/raw_pdfs"
parsed_dir = "data/parsed"

for old_pdf, meta in clean_mapping.items():
    new_pdf = meta["new_file"]
    old_json = old_pdf.replace(".pdf", ".json")
    new_json = new_pdf.replace(".pdf", ".json")
    
    old_pdf_path = os.path.join(raw_dir, old_pdf)
    new_pdf_path = os.path.join(raw_dir, new_pdf)
    if os.path.exists(old_pdf_path):
        os.rename(old_pdf_path, new_pdf_path)
        
    old_json_path = os.path.join(parsed_dir, old_json)
    new_json_path = os.path.join(parsed_dir, new_json)
    if os.path.exists(old_json_path):
        os.rename(old_json_path, new_json_path)

# 3. Update Postgres DB
conn = psycopg2.connect(dbname="nexus_db", user="nexus", password="password", host="localhost", port=5434)
cur = conn.cursor()

for old_pdf, meta in clean_mapping.items():
    new_pdf = meta["new_file"]
    title = meta["title"]
    author_name = meta["author"]
    
    # Update title and filename
    cur.execute("UPDATE papers SET title = %s, filename = %s WHERE filename = %s RETURNING id;", (title, new_pdf, old_pdf))
    row = cur.fetchone()
    if row:
        paper_id = row[0]
        # Insert author
        cur.execute("INSERT INTO authors (id, name) VALUES (gen_random_uuid(), %s) ON CONFLICT (name) DO UPDATE SET name=EXCLUDED.name RETURNING id;", (author_name,))
        author_id = cur.fetchone()[0]
        # Link author
        cur.execute("INSERT INTO paper_authors (paper_id, author_id) VALUES (%s, %s) ON CONFLICT DO NOTHING;", (paper_id, author_id))

conn.commit()
cur.close()
conn.close()

# 4. Update ChromaDB Metadata
client = chromadb.PersistentClient(path="./data/chromadb")
coll = client.get_collection("database_papers")

# Fetch all metadata and update
data = coll.get()
ids = data["ids"]
metadatas = data["metadatas"]

updates_needed = False
for i in range(len(metadatas)):
    old_source = metadatas[i].get("source")
    if old_source:
        old_pdf = old_source.replace(".json", ".pdf")
        if old_pdf in clean_mapping:
            new_source = clean_mapping[old_pdf]["new_file"].replace(".pdf", ".json")
            if metadatas[i]["source"] != new_source:
                metadatas[i]["source"] = new_source
                updates_needed = True

if updates_needed:
    # ChromaDB update requires chunking if it's large, but we can update in batches
    batch_size = 1000
    for i in range(0, len(ids), batch_size):
        batch_ids = ids[i:i+batch_size]
        batch_metas = metadatas[i:i+batch_size]
        coll.update(ids=batch_ids, metadatas=batch_metas)
    print("ChromaDB updated.")

print("All done!")
