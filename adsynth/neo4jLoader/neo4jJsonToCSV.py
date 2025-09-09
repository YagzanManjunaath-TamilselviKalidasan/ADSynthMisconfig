import json
import csv
from neo4j import GraphDatabase


# Connect to Neo4j
# driver = GraphDatabase.driver(
#     "bolt://localhost:7687", auth=("neo4j", "password"))


file_name = '2025-08-20_11-27-01-044'


def main():
    try:

        data = []

        with open(f"../../generated_datasets/{file_name}.json", "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():  # skip empty lines
                    data.append(json.loads(line))

        print(len(data), "records loaded")
        print(data[0])  # show first record

        print(f"Converting {file_name}.json to {file_name}.csv")
        # Load JSON
        first = data[0]
        fieldnames = ["id", "labels", "type", "description", "blocksInheritance", "admincount",'inheritanceType','isacl','fromgpo','isinherited','isInherited', 'enforced', 'lastlogon', 'unconstraineddelegation', 'pwdlastset', 'sensitive', 'serviceprincipalnames', 'dontreqpreauth', 'passwordnotreqd', 'hasspn', 'pwdneverexpires', 'lastlogontimestamp', 'savedcredentials', 'enabled', 'sidhistory', 'displayname', 'gpcpath', 'exploitable', 'privesc', 'creddump', 'operatingsystem', 'haslaps', 'title', 'homedirectory', 'userpassword', 'special_role', 'email'] + \
            list(first["properties"].keys())
        with open(f"../../generated_datasets/{file_name}.csv", "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for line in data:
                props = line.get("properties", {})
                if not isinstance(props, dict):
                    props = {}

                # Build row, skipping if a field is missing
                row = {
                    "id": line.get("id", ""),       # default "" if missing
                    "type": line.get("type", ""),   # default "" if missing
                    **{k: props.get(k, "") for k in props}
                }
                writer.writerow(row)
    except Exception as err:
        print(f"Error occurred : {err}")


if __name__ == "__main__":
    main()
