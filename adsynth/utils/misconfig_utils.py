import json
import os
from datetime import datetime
import tempfile
import networkx as nx
from adsynth.DATABASE import NODES, EDGES, MISCONFIGURED_SESSION, MISCONFIGURED_SESSION_USERS
import matplotlib.pyplot as plt


def populate_admin_users(NODES):
    pass


def update_db(session, operation):
    # print("Dump to JSON file")
    current_datetime = datetime.now()
    # Format the date and time to include seconds
    filename = current_datetime.strftime("%Y-%m-%d_%H-%M-%S-%f")[:-3]

    with open(f"generated_datasets/{filename}-{operation}.json", "w") as f:
        for obj in NODES:
            obj["type"] = "node"
            # Use json.dumps() to convert the object to a JSON string without square brackets
            json_str = json.dumps(obj, separators=(',', ':'))
            # Write the JSON string to the file with a newline character
            f.write(json_str + '\n')

    # Open the file in append mode
    with open(f"generated_datasets/{filename}-{operation}.json", 'a') as f:
        for obj in EDGES:
            # Use json.dumps() to convert the object to a JSON string without square brackets
            json_str = json.dumps(obj, separators=(',', ':'))
            # Write the JSON string to the file with a newline character
            f.write(json_str + '\n')

    # ===============================================

    path = f"{os.getcwd()}/generated_datasets/{filename}-{operation}.json"

    query = f"PROFILE CALL apoc.periodic.iterate(\"CALL apoc.import.json('{path}')\", \"RETURN 1\", {{batchSize:1000}})"

    session.run(query)
    session.close()


# todo Should we include only exploitable permissions
def check_shortest_paths_from_misconfigured_users_using_cypher(session, round, rows, domain_grp_name):
    for user in MISCONFIGURED_SESSION_USERS:
        query = f"""
            MATCH (u:User {{name:'{user}'}}),
                (g:Group {{name:'{domain_grp_name}'}})
                MATCH p = shortestPath((u)-[*1..]->(g))
                RETURN p, length(p) AS pathLength;
                """

        results = session.run(query)

        for record in results:
            path = record["p"]
            path_len = record["pathLength"]

            node_names = [n.get("name") or n.get("displayname") for n in path.nodes]
            path_str = " -> ".join(node_names)
            if user not in rows:
                rows[user] = {}

            rows[user][f"path_length itr {round}"] = path_len
            # rows[user].append({
            #   "EntryPoint": user,
            #  "path_length ": path_len,
            # "path_str": path_str,
            # "nodes": node_names
            # })


def check_shortest_paths_from_misconfigured_users_using_cypher(session, round, rows, domain_grp_name):
    for user in MISCONFIGURED_SESSION_USERS:
        query = f"""
            MATCH (u:User {{name:'{user}'}}),
                (g:Group {{name:'{domain_grp_name}'}})
                MATCH p = shortestPath((u)-[*1..]->(g))
                RETURN p, length(p) AS pathLength;
                """

        results = session.run(query)

        for record in results:
            path = record["p"]
            path_len = record["pathLength"]

            node_names = [n.get("name") or n.get("displayname") for n in path.nodes]
            path_str = " -> ".join(node_names)
            if user not in rows:
                rows[user] = {}

            rows[user][f"path_length itr {round}"] = path_len
            # rows[user].append({
            #   "EntryPoint": user,
            #  "path_length ": path_len,
            # "path_str": path_str,
            # "nodes": node_names
            # })


def update_db_with_temp_file(session, operation):
    # print("Dump to JSON temp file")
    current_datetime = datetime.now()
    filename_suffix = current_datetime.strftime("%Y-%m-%d_%H-%M-%S-%f")[:-3]

    # Create a temporary file with delete=False so APOC can read it
    with tempfile.NamedTemporaryFile(
            mode="w", suffix=f"-{operation}.json", prefix=filename_suffix, dir=".", delete=False
    ) as tmpfile:
        temp_path = tmpfile.name

        # Write nodes
        for obj in NODES:
            obj["type"] = "node"
            json_str = json.dumps(obj, separators=(',', ':'))
            tmpfile.write(json_str + '\n')

        # Write edges
        for obj in EDGES:
            json_str = json.dumps(obj, separators=(',', ':'))
            tmpfile.write(json_str + '\n')

    abs_path = os.path.abspath(temp_path)

    query = (
        f"PROFILE CALL apoc.periodic.iterate("
        f"\"CALL apoc.import.json('{abs_path}')\", "
        f"\"RETURN 1\", {{batchSize:1000}})"
    )

    session.run(query)
    session.close()

    # Clean up file afterwards
    os.remove(abs_path)


def check_session_info(session):
    for key, value in MISCONFIGURED_SESSION.items():

        query = f"MATCH p = (u:User {{name:'{value}'}})-[:HasSession]->(c:Computer) RETURN p"

        results = session.run(query)
        for record in results:
            path = record["p"]
            print("Path:")
            for node in path.nodes:
                print("  Node:", dict(node))
            for rel in path.relationships:
                print("  Relationship:", rel.type, dict(rel))
