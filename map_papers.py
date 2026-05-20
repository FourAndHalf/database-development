import json

papers = [
    "bigtable-osdi06.pdf",
    "omega_flexible_scalable_multi_database_concurrency_control.pdf",
    "pacelc_theorem.pdf",
    "c_store_a_column_oriented_dbms.pdf",
    "dynamo_amazons_highly_available_key_value_store.pdf",
    "pnuts_yahoos_hosted_data_serving_platform.pdf",
    "megastore_and_megastore_extended_consistency.pdf",
    "wisckey.pdf",
    "viewstamped_replication.pdf",
    "WiredTiger__A_High_Performance_NoSQL_Database_Engine.pdf",
    "the_chubby_lock_service_for_loosely_coupled_distributed_systems.pdf",
    "global_secondary_indexes_in_f1.pdf",
    "cassandra_a_decentralized_structured_storage_system.pdf",
    "viewstamped_replication_revisited.pdf",
    "bigtable_vs_cassandra_vs_dynamo.pdf",
    "Amazon_SimpleDB.pdf",
    "dremel_interactive_analysis_of_web_scale_datasets.pdf",
    "pig_hive.pdf",
    "evolution_of_development_priorities_in_key_value_stores_serving_large_scale_applications_the_rocksdb_experience.pdf",
    "TPC_C__TPC_H_Benchmarks.pdf",
    "chain_replication_for_supporting_high_throughput_and_availability.pdf",
    "systemml_spark_sql.pdf",
    "bigTable-paper.pdf",
    "wisckey_separating_keys_from_values_in_ssd_conscious_storage.pdf",
    "paxos_made_practical.pdf",
    "line.pdf",
    "spanner_googles_globally_distributed_database.pdf",
    "tapir.pdf",
    "redblue_consistency.pdf",
    "secondary_indexes_in_distributed_dbs.pdf",
    "google_file_system.pdf",
    "consistency_without_partition.pdf",
    "rocksdb_evolution_of_development_priorities_in_a_key_value_store.pdf",
    "TPC_C__TPC_H__TPC_DS.pdf",
    "megastore_scalable_highly_available_storage_for_interactive_services.pdf",
    "pacelc.pdf",
    "paxos_made_simple.pdf",
    "calvin_fast_distributed_transactions.pdf",
    "madlib_scalable_sql_analytics.pdf",
    "totalstore_combining_paxos_with_batch_processing.pdf",
    "calm_theorem.pdf",
    "Riak__A_Distributed__Eventually_Consistent_Key_Value_Data_Store.pdf",
    "bigtable_a_distributed_storage_system_for_structured_data.pdf",
    "f1_a_distributed_sql_database_that_scales.pdf",
    "the_bigdawg_polystore_system_and_architecture.pdf",
    "hyperdex.pdf",
    "the_chubby_lock_service.pdf",
    "cap_theorem.pdf",
    "zookeeper_wait_free_coordination_for_internet_scale_systems.pdf",
    "spanners_consistency.pdf",
    "TPCC__TPC_DS__TPC_H.pdf",
    "silt.pdf",
    "amazon_dynamodb_a_scalable_predictably_performant_and_fully_managed_nosql_database_service.pdf",
    "consistent_hashing.pdf",
    "HBase__The_Hadoop_Database.pdf",
    "ycsb_yahoo_cloud_serving_benchmark.pdf",
    "raft_in_search_of_an_understandable_consensus_algorithm.pdf",
    "numas_in_network_query_processing.pdf",
    "flexible_paxos.pdf",
    "oltp_bench.pdf",
    "Aerospike.pdf"
]

def clean_name(f):
    name = f.replace(".pdf", "").replace("_", " ").replace("-", " ")
    name = " ".join([w.capitalize() for w in name.split()])
    return name

mapping = {}
for p in papers:
    title = clean_name(p)
    new_filename = p.replace(".pdf", "")
    # specific overrides
    if "dynamo" in p.lower() and "amazon" in p.lower():
        title = "Dynamo: Amazon's Highly Available Key-Value Store"
        author = "Giuseppe DeCandia et al."
    elif "spanner" in p.lower():
        title = "Spanner: Google's Globally Distributed Database"
        author = "James C. Corbett et al."
    elif "bigtable" in p.lower() and "osdi" in p.lower():
        title = "Bigtable: A Distributed Storage System for Structured Data"
        author = "Fay Chang et al."
    elif "cassandra" in p.lower() and "decentralized" in p.lower():
        title = "Cassandra: A Decentralized Structured Storage System"
        author = "Avinash Lakshman, Prashant Malik"
    elif "raft" in p.lower():
        title = "In Search of an Understandable Consensus Algorithm (Raft)"
        author = "Diego Ongaro, John Ousterhout"
    elif "paxos_made_simple" in p.lower():
        title = "Paxos Made Simple"
        author = "Leslie Lamport"
    elif "google_file_system" in p.lower():
        title = "The Google File System"
        author = "Sanjay Ghemawat et al."
    elif "mapreduce" in p.lower():
        title = "MapReduce: Simplified Data Processing on Large Clusters"
        author = "Jeffrey Dean, Sanjay Ghemawat"
    elif "zookeeper" in p.lower():
        title = "ZooKeeper: Wait-free Coordination for Internet-scale Systems"
        author = "Patrick Hunt et al."
    elif "chubby" in p.lower():
        title = "The Chubby Lock Service for Loosely-Coupled Distributed Systems"
        author = "Mike Burrows"
    elif "cap" in p.lower():
        title = "Brewer's Conjecture and the Feasibility of Consistent, Available, Partition-Tolerant Web Services"
        author = "Seth Gilbert, Nancy Lynch"
    elif "pacelc" in p.lower():
        title = "PACELC Theorem"
        author = "Daniel J. Abadi"
    elif "dremel" in p.lower():
        title = "Dremel: Interactive Analysis of Web-Scale Datasets"
        author = "Sergey Melnik et al."
    else:
        author = "Unknown Author"

    mapping[p] = {
        "title": title,
        "author": author
    }

with open("paper_mapping.json", "w") as f:
    json.dump(mapping, f, indent=2)
