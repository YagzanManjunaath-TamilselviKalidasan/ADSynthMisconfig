import csv
import json
import re
import ast
import os
from datetime import datetime
import tempfile
import networkx as nx
import pandas as pd

from adsynth.DATABASE import NODES, EDGES
import matplotlib.pyplot as plt

from adsynth.EXPERIMENT_DATABASE import EXP_MISCONFIGURED_SESSION, EXP_MISCONFIGURED_SESSION_USERS, EXP_NODES, \
    EXP_EDGES, EXP_MISCONFIGURED_PERMISSION


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
    for user in EXP_MISCONFIGURED_SESSION_USERS:
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
    for user in EXP_MISCONFIGURED_SESSION_USERS:
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


def check_session_info(session):
    for key, value in EXP_MISCONFIGURED_SESSION.items():

        query = f"MATCH p = (u:User {{name:'{value}'}})-[:HasSession]->(c:Computer) RETURN p"

        results = session.run(query)
        for record in results:
            path = record["p"]
            print("Path:")
            for node in path.nodes:
                print("  Node:", dict(node))
            for rel in path.relationships:
                print("  Relationship:", rel.type, dict(rel))


def export_user_level_data_to_csv(misconfig_metrics_per_itr, filename_prefix="session_misconfig_user_data"):
    output_dir = f"{os.getcwd()}/generated_datasets/"

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_filename = f"{filename_prefix}_{timestamp}.csv"
    csv_path = os.path.join(output_dir, csv_filename)

    os.makedirs(output_dir, exist_ok=True)

    rows = [["Iteration", "Misconfig Step", "User", "Groups"]]

    for itr, itr_metrics in misconfig_metrics_per_itr.items():
        for step, step_data in itr_metrics.items():
            users_meta = step_data.get("reachable_users", [])
            for meta in users_meta:

                if " - " in meta:
                    user_name, group_part = meta.split(" - ", 1)
                    groups = group_part.strip("[]")
                else:
                    user_name, groups = meta, ""
                rows.append([itr, step, user_name.strip(), groups.strip()])

    # Write to CSV
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerows(rows)

    print(f"Exported user-level data to CSV: {csv_path}")
    return csv_path


def analyze_group_surges_from_csv(csv_path):
    df = pd.read_csv(csv_path)
    df = df.assign(Groups=df["Groups"].fillna("").str.split(","))
    df = df.explode("Groups")
    df["Groups"] = df["Groups"].str.strip()

    group_counts = (
        df.groupby(["Iteration", "Misconfig Step", "Groups"])
        .agg(User_Count=("User", "nunique"))
        .reset_index()
        .sort_values(["Iteration", "Misconfig Step", "User_Count"], ascending=[True, True, False])
    )

    group_counts["Prev_Count"] = group_counts.groupby(["Iteration", "Groups"])["User_Count"].shift(1)
    group_counts["Surge"] = group_counts["User_Count"] - group_counts["Prev_Count"].fillna(0)

    print("Computed group-level surges per step")
    return group_counts


def tabulate_experiment_results(session, misconfig_growth_metrics, misconfig_type="test"):
    query_template = """
                     WITH $pair AS pair
                     WITH split(pair, '->') AS parts
                     WITH trim (parts[0]) AS compName, trim (parts[1]) AS userName
                         MATCH (c :Computer {name : compName})
                         OPTIONAL MATCH (ouC:OU)-[: Contains]->(c)
                         OPTIONAL MATCH (c)-[:MemberOf]->(grpC: Group)
                         OPTIONAL MATCH (c)-[:HasSession]->(uSession: User)
                     WITH
                         c, collect(DISTINCT ouC.name) AS compOUs, collect(DISTINCT grpC.name) AS compGroups, collect(DISTINCT uSession.name) AS allSessionUsers, userName
                         MATCH (u: User {name : userName})
                         OPTIONAL MATCH (ouU:OU)-[: Contains]->(u)
                         OPTIONAL MATCH (u)-[:MemberOf]->(grpU: Group)
                         OPTIONAL MATCH (u)-[:HasSession]->(compU:Computer)

                     WITH
                         c, compOUs, compGroups, allSessionUsers, u, collect(DISTINCT ouU.name) AS userOUs, collect(DISTINCT grpU.name) AS userGroups, collect(DISTINCT compU.name) AS userSessionComputers

                     WITH
                         c, compOUs, compGroups, [x IN allSessionUsers
                     WHERE x <> u.name] AS otherSessionUsers
                         , u
                         , userOUs
                         , userGroups
                         , userSessionComputers
                         RETURN
                         c.name AS Computer
                         , compOUs AS ComputerOUs
                         , compGroups AS ComputerGroups
                         , otherSessionUsers AS OtherUsersWithSessionOnComputer
                         , u.name AS User
                         , userOUs AS UserOUs
                         , userGroups AS UserGroups
                         , userSessionComputers AS ComputersWhereUserHasSession

                     """
    import re
    import ast

    results = []


    for i in sorted(EXP_MISCONFIGURED_SESSION.keys(), key=lambda x: int(x)):
        pair = EXP_MISCONFIGURED_SESSION[i]
        i = int(i)
        result = session.run(query_template, {"pair": pair})
        record = result.single()
        if record:
            results.append({
                "Iteration": i,
                "comp → user": pair.replace("->", " → "),
                "Computer": record["Computer"],
                "User": record["User"],
                "ComputerOUs": record["ComputerOUs"],
                "ComputerGroups": record["ComputerGroups"],
                "OtherUsersWithSessionOnComputer": record["OtherUsersWithSessionOnComputer"],
                "UserOUs": record["UserOUs"],
                "UserGroups": record["UserGroups"],
                "ComputersWhereUserHasSession": record["ComputersWhereUserHasSession"],
                "ReachableComps": misconfig_growth_metrics[i]["new_reachable_comps_names"],
                "ReachableUsers": misconfig_growth_metrics[i]["new_reachable_users"]
            })

    if misconfig_type == "session":
        pass
    else:
        for i in sorted(EXP_MISCONFIGURED_PERMISSION.keys(), key=lambda x: int(x)):
            pair = EXP_MISCONFIGURED_PERMISSION[i]
            i =int(i)
            result = session.run(query_template, {"pair": pair})
            record = result.single()
            if record:
                results.append({
                    "Iteration":  (10 +  i),
                    "comp → user": pair.replace("->", " → "),
                    "Computer": record["Computer"],
                    "User": record["User"],
                    "ComputerOUs": record["ComputerOUs"],
                    "ComputerGroups": record["ComputerGroups"],
                    "OtherUsersWithSessionOnComputer": record["OtherUsersWithSessionOnComputer"],
                    "UserOUs": record["UserOUs"],
                    "UserGroups": record["UserGroups"],
                    "ComputersWhereUserHasSession": record["ComputersWhereUserHasSession"],
                    "ReachableComps": misconfig_growth_metrics[i]["new_reachable_comps_names"],
                    "ReachableUsers": misconfig_growth_metrics[i]["new_reachable_users"]
                })

    # --- Markdown table header (added Exploit column) ---
    print(
        "| Iteration | comp → user | Computer | User | Computer OUs | Computer Groups | Other Users w/ Session on Computer | User OUs | User Groups | Computers Where User Has Session | Reachable Comps | Reachable User count | Reachable User | Exploit | Groups |"
    )
    print(
        "|-----------:|-------------|-----------|------|---------------|-----------------|------------------------------------|-----------|-------------|----------------------------------|----------------------|----------------------|----------------|---------|---------|"
    )

    # --- Print rows ---
    for r in results:
        comp_ous = ', '.join(r.get('ComputerOUs') or [])
        comp_groups = ', '.join(r.get('ComputerGroups') or [])
        other_users = ', '.join(r.get('OtherUsersWithSessionOnComputer') or [])
        user_ous = ', '.join(r.get('UserOUs') or [])
        user_groups = ', '.join(r.get('UserGroups') or [])
        user_comps = ', '.join(r.get('ComputersWhereUserHasSession') or [])

        # tolerant reachable_comps fetch (various key namings you've used)
        reachable_comps_val = r.get('ReachableComps') or r.get('reachable_comps_names') or r.get(
            'reachable_comps') or r.get('ReachableCompsNames') or []
        if isinstance(reachable_comps_val, (list, set, tuple)):
            reachable_comps = ', '.join(reachable_comps_val)
        else:
            reachable_comps = str(reachable_comps_val)

        # Normalize reachable users field and count
        reachable_raw = r.get("ReachableUsers") or []
        if isinstance(reachable_raw, str):
            try:
                reachable_raw = ast.literal_eval(reachable_raw)
            except Exception:
                reachable_raw = [reachable_raw]
        # ensure it's a list
        if not isinstance(reachable_raw, (list, tuple)):
            reachable_raw = [reachable_raw]

        reachable_user_count = len(reachable_raw)

        parsed_reachables = []
        # more tolerant pattern: capture any user text before " - ["
        pattern = re.compile(r"^(?P<user>.*?)\s*-\s*\[(?P<groups>.*)\]\s*(?:-\s*(?P<exploit>.*))?$")

        for entry in reachable_raw:
            if not entry:
                continue
            # if entry already structured (dict/tuple), handle common shapes
            if isinstance(entry, dict):
                user = entry.get('user') or entry.get('name') or ""
                groups = entry.get('groups') or entry.get('member_of') or []
                exploit = entry.get('exploits') or entry.get('exploit') or entry.get('exploit_type') or ""
                # normalize groups/exploit to strings/lists
                if isinstance(groups, str):
                    try:
                        groups = ast.literal_eval(groups)
                    except Exception:
                        groups = [groups]
                if isinstance(exploit, (list, tuple)):
                    exploit_cell = ", ".join(map(str, exploit))
                else:
                    exploit_cell = str(exploit) if exploit else ""
                parsed_reachables.append((user.strip(), groups, exploit_cell))
                continue

            # normalize tuple/list entries
            if isinstance(entry, (list, tuple)):
                # common shape: ("user - [..] - exploit",) or (user, groups, exploit)
                if len(entry) == 1 and isinstance(entry[0], str):
                    entry = entry[0]
                elif len(entry) >= 2:
                    user = str(entry[0])
                    groups = entry[1] if isinstance(entry[1], (list, tuple)) else [str(entry[1])]
                    exploit_cell = ", ".join(map(str, entry[2:])) if len(entry) > 2 else ""
                    parsed_reachables.append((user.strip(), groups, exploit_cell))
                    continue

            # entry now expected to be a string like "User - ['G1', 'G2'] - successor(HasSession)"
            entry_str = str(entry).strip()
            m = pattern.match(entry_str)
            if m:
                user = m.group("user").strip()
                groups_str = m.group("groups").strip()
                exploit = (m.group("exploit") or "").strip()

                # parse groups safely
                groups = []
                if groups_str:
                    try:
                        groups = ast.literal_eval(f"[{groups_str}]")
                    except Exception:
                        # fallback: split on commas, strip quotes/spaces
                        groups = [g.strip().strip("'\"") for g in groups_str.split(",") if g.strip()]

                # normalize exploit field
                exploit_cell = ""
                if exploit:
                    # if exploit looks like "predecessor(...)" keep normalized spacing
                    if "(" in exploit and exploit.endswith(")"):
                        prefix, inner = exploit.split("(", 1)
                        inner = inner[:-1]
                        items = [s.strip() for s in re.split(r",\s*", inner) if s.strip()]
                        exploit_cell = f"{prefix.strip()}({', '.join(items)})"
                    else:
                        # could be comma-separated list or single token
                        try:
                            parsed = ast.literal_eval(exploit) if exploit.startswith("[") else [s.strip() for s in
                                                                                                exploit.split(",")]
                            exploit_cell = ", ".join(parsed)
                        except Exception:
                            exploit_cell = exploit
                parsed_reachables.append((user, groups, exploit_cell))
            else:
                # fallback: treat whole string as user with empty groups/exploit
                parsed_reachables.append((entry_str, [], ""))

        # --- Output rows (first row includes main fields, subsequent rows only reachable-user/exploit/groups) ---
        for idx, (reachable_user, groups, exploit_cell) in enumerate(parsed_reachables):
            group_lines = "<br>".join(groups or [" "])  # vertical list
            exploit_display = exploit_cell or " "
            if idx == 0:
                print(
                    f"| {r.get('Iteration', '')} "
                    f"| `{r.get('comp → user', '')}` "
                    f"| `{r.get('Computer', '')}` "
                    f"| `{r.get('User', '')}` "
                    f"| `{comp_ous}` "
                    f"| `{comp_groups}` "
                    f"| `{other_users}` "
                    f"| `{user_ous}` "
                    f"| `{user_groups}` "
                    f"| `{user_comps}` "
                    f"| `{reachable_comps}` "
                    f"| `{reachable_user_count}` "
                    f"| `{reachable_user}` "
                    f"| `{exploit_display}` "
                    f"| {group_lines} |"
                )
            else:
                # subsequent rows: keep main columns empty for visual grouping
                print(
                    f"|  |  |  |  |  |  |  |  |  |  |  |  | `{reachable_user}` | `{exploit_display}` | {group_lines} |"
                )
    return results
