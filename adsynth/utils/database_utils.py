import copy
import json
import os
import tempfile
from datetime import datetime

from adsynth.DATABASE import *
from adsynth.EXPERIMENT_DATABASE import *

import json
import os
import gzip
from pathlib import Path
from typing import Any, Dict

EXPERIMENT_STATES = {}


def init_experiment_state(iteration_index: int = 0, verbose: bool = False):
    EXP_NODES[:] = copy.deepcopy(NODES)
    EXP_EDGES[:] = copy.deepcopy(EDGES)
    EXP_DATABASE_ID.clear()
    EXP_DATABASE_ID.update(copy.deepcopy(DATABASE_ID))
    EXP_dict_edges.clear()
    EXP_dict_edges.update(copy.deepcopy(dict_edges))
    EXP_NODE_GROUPS.clear()
    EXP_NODE_GROUPS.update(copy.deepcopy(NODE_GROUPS))

    EXP_GPLINK_OUS[:] = copy.deepcopy(GPLINK_OUS)
    EXP_GROUP_MEMBERS.clear()
    EXP_GROUP_MEMBERS.update(copy.deepcopy(GROUP_MEMBERS))
    EXP_SECURITY_GROUPS[:] = copy.deepcopy(SECURITY_GROUPS)
    EXP_ADMIN_USERS[:] = copy.deepcopy(ADMIN_USERS)
    EXP_ENABLED_USERS[:] = copy.deepcopy(ENABLED_USERS)
    EXP_DISABLED_USERS[:] = copy.deepcopy(DISABLED_USERS)

    EXP_PAW_TIERS[:] = copy.deepcopy(PAW_TIERS)
    EXP_S_TIERS[:] = copy.deepcopy(S_TIERS)
    EXP_S_TIERS_LOCATIONS[:] = copy.deepcopy(S_TIERS_LOCATIONS)
    EXP_WS_TIERS[:] = copy.deepcopy(WS_TIERS)
    EXP_WS_TIERS_LOCATIONS[:] = copy.deepcopy(WS_TIERS_LOCATIONS)

    EXP_COMPUTERS[:] = copy.deepcopy(COMPUTERS)
    EXP_ridcount[:] = copy.deepcopy(ridcount)
    EXP_KERBEROASTABLES[:] = copy.deepcopy(KERBEROASTABLES)
    EXP_FOLDERS[:] = copy.deepcopy(FOLDERS)
    EXP_DISTRIBUTION_GROUPS[:] = copy.deepcopy(DISTRIBUTION_GROUPS)
    EXP_SEC_DIST_GROUPS[:] = copy.deepcopy(SEC_DIST_GROUPS)
    EXP_LOCAL_ADMINS[:] = copy.deepcopy(LOCAL_ADMINS)

    # Misconfiguration state
    EXP_MISCONFIGURED_SESSION_COMPUTERS[:] = []
    EXP_MISCONFIGURED_SESSION_USERS[:] = []
    EXP_MISCONFIGURED_SESSION.clear()


    EXP_MISCONFIGURED_PERMISSION_COMPUTERS[:] = []
    EXP_MISCONFIGURED_PERMISSION_USERS[:] = []
    EXP_MISCONFIGURED_PERMISSION.clear()

    EXP_MISCONFIGURED_GRP_PERMISSION.clear()
    EXP_MISCONFIGURED_GRP_NESTING.clear()

    global EXP_neo4j_id
    EXP_neo4j_id = neo4j_id

    snapshot = {
        "nodes": copy.deepcopy(EXP_NODES),
        "edges": copy.deepcopy(EXP_EDGES),
        "database_id": copy.deepcopy(EXP_DATABASE_ID),
        "dict_edges": copy.deepcopy(EXP_dict_edges),
        "node_groups": copy.deepcopy(EXP_NODE_GROUPS),
        "security_groups": copy.deepcopy(EXP_SECURITY_GROUPS),
        "admin_users": copy.deepcopy(EXP_ADMIN_USERS),
        "enabled_users": copy.deepcopy(EXP_ENABLED_USERS),
        "disabled_users": copy.deepcopy(EXP_DISABLED_USERS),
        "paw_tiers": copy.deepcopy(EXP_PAW_TIERS),
        "s_tiers": copy.deepcopy(EXP_S_TIERS),
        "ws_tiers": copy.deepcopy(EXP_WS_TIERS),
        "computers": copy.deepcopy(EXP_COMPUTERS),
        "folders": copy.deepcopy(EXP_FOLDERS),
        "kerberoastables": copy.deepcopy(EXP_KERBEROASTABLES),
        "local_admins": copy.deepcopy(EXP_LOCAL_ADMINS),
        "misconfig_session": copy.deepcopy(EXP_MISCONFIGURED_SESSION),
        "misconfig_permission": copy.deepcopy(EXP_MISCONFIGURED_PERMISSION),
        "misconfig_grp_permission": copy.deepcopy(EXP_MISCONFIGURED_GRP_PERMISSION),
        "misconfig_grp_nesting": copy.deepcopy(EXP_MISCONFIGURED_GRP_NESTING),
        "misconfig_session_users": copy.deepcopy(EXP_MISCONFIGURED_SESSION_USERS),
        "misconfig_session_computers": copy.deepcopy(EXP_MISCONFIGURED_SESSION_COMPUTERS),
        "misconfig_permissions_users": copy.deepcopy(EXP_MISCONFIGURED_PERMISSION_USERS),
        "misconfig_permissions_computers": copy.deepcopy(EXP_MISCONFIGURED_PERMISSION_COMPUTERS),
        "neo4j_id": EXP_neo4j_id,
    }
    global EXPERIMENT_STATES

    EXPERIMENT_STATES[iteration_index] = snapshot

    if verbose:
        print(f" Experiment DB initialized from base ADSynth state")
        print(f"   • Nodes: {len(EXP_NODES)} from {len(NODES)}")
        print(f"   • Edges: {len(EXP_EDGES)}  from {len(EDGES)}")
        print(f"   • Security Groups: {len(EXP_SECURITY_GROUPS)}  from {len(EXP_SECURITY_GROUPS)}")

    return {
        "nodes": len(EXP_NODES),
        "edges": len(EXP_EDGES),
        "security_groups": len(EXP_SECURITY_GROUPS),
        "neo4j_id": EXP_neo4j_id
    }


def save_experiment_state(iteration_index: int, verbose: bool = False):
    global EXPERIMENT_STATES

    snapshot = {
        "nodes": copy.deepcopy(EXP_NODES),
        "edges": copy.deepcopy(EXP_EDGES),
        "database_id": copy.deepcopy(EXP_DATABASE_ID),
        "dict_edges": copy.deepcopy(EXP_dict_edges),
        "node_groups": copy.deepcopy(EXP_NODE_GROUPS),
        "security_groups": copy.deepcopy(EXP_SECURITY_GROUPS),
        "admin_users": copy.deepcopy(EXP_ADMIN_USERS),
        "enabled_users": copy.deepcopy(EXP_ENABLED_USERS),
        "disabled_users": copy.deepcopy(EXP_DISABLED_USERS),
        "paw_tiers": copy.deepcopy(EXP_PAW_TIERS),
        "s_tiers": copy.deepcopy(EXP_S_TIERS),
        "ws_tiers": copy.deepcopy(EXP_WS_TIERS),
        "computers": copy.deepcopy(EXP_COMPUTERS),
        "folders": copy.deepcopy(EXP_FOLDERS),
        "kerberoastables": copy.deepcopy(EXP_KERBEROASTABLES),
        "local_admins": copy.deepcopy(EXP_LOCAL_ADMINS),
        "misconfig_session": copy.deepcopy(EXP_MISCONFIGURED_SESSION),
        "misconfig_permission": copy.deepcopy(EXP_MISCONFIGURED_PERMISSION),
        "misconfig_grp_permission": copy.deepcopy(EXP_MISCONFIGURED_GRP_PERMISSION),
        "misconfig_grp_nesting": copy.deepcopy(EXP_MISCONFIGURED_GRP_NESTING),
        "misconfig_session_users": copy.deepcopy(EXP_MISCONFIGURED_SESSION_USERS),
        "misconfig_session_computers": copy.deepcopy(EXP_MISCONFIGURED_SESSION_COMPUTERS),
        "misconfig_permissions_users": copy.deepcopy(EXP_MISCONFIGURED_PERMISSION_USERS),
        "misconfig_permissions_computers": copy.deepcopy(EXP_MISCONFIGURED_PERMISSION_COMPUTERS),
        "neo4j_id": copy.deepcopy(EXP_neo4j_id),
    }

    EXPERIMENT_STATES[iteration_index] = snapshot

    if verbose:
        print(f"💾 Saved experiment state for iteration {iteration_index}")
        print(f"   • Nodes: {len(EXP_NODES)}")
        print(f"   • Edges: {len(EXP_EDGES)}")
        print(f"   • Security Groups: {len(EXP_SECURITY_GROUPS)}")

    return {
        "iteration": iteration_index,
        "nodes": len(EXP_NODES),
        "edges": len(EXP_EDGES),
        "security_groups": len(EXP_SECURITY_GROUPS),
        "neo4j_id": EXP_neo4j_id,
    }


def restore_experiment_state(iteration_index: int = 0, verbose: bool = False):
    global EXPERIMENT_STATES
    if iteration_index not in EXPERIMENT_STATES:
        raise KeyError(f"No saved experiment state found for iteration {iteration_index}")

    snapshot = EXPERIMENT_STATES[iteration_index]

    EXP_NODES[:] = copy.deepcopy(snapshot["nodes"])
    EXP_EDGES[:] = copy.deepcopy(snapshot["edges"])
    EXP_DATABASE_ID.clear()
    EXP_DATABASE_ID.update(copy.deepcopy(snapshot["database_id"]))
    EXP_dict_edges.clear()
    EXP_dict_edges.update(copy.deepcopy(snapshot["dict_edges"]))
    EXP_NODE_GROUPS.clear()
    EXP_NODE_GROUPS.update(copy.deepcopy(snapshot["node_groups"]))

    EXP_SECURITY_GROUPS[:] = copy.deepcopy(snapshot["security_groups"])
    EXP_ADMIN_USERS[:] = copy.deepcopy(snapshot["admin_users"])
    EXP_ENABLED_USERS[:] = copy.deepcopy(snapshot["enabled_users"])
    EXP_DISABLED_USERS[:] = copy.deepcopy(snapshot["disabled_users"])

    EXP_PAW_TIERS[:] = copy.deepcopy(snapshot["paw_tiers"])
    EXP_S_TIERS[:] = copy.deepcopy(snapshot["s_tiers"])
    EXP_WS_TIERS[:] = copy.deepcopy(snapshot["ws_tiers"])
    EXP_COMPUTERS[:] = copy.deepcopy(snapshot["computers"])
    EXP_FOLDERS[:] = copy.deepcopy(snapshot["folders"])
    EXP_KERBEROASTABLES[:] = copy.deepcopy(snapshot["kerberoastables"])
    EXP_LOCAL_ADMINS[:] = copy.deepcopy(snapshot["local_admins"])
    EXP_MISCONFIGURED_SESSION.clear()
    EXP_MISCONFIGURED_SESSION.update(copy.deepcopy(snapshot["misconfig_session"]))
    EXP_MISCONFIGURED_PERMISSION.clear()
    EXP_MISCONFIGURED_PERMISSION.update(copy.deepcopy(snapshot["misconfig_permission"]))
    EXP_MISCONFIGURED_GRP_PERMISSION.clear()
    EXP_MISCONFIGURED_GRP_PERMISSION.update(copy.deepcopy(snapshot["misconfig_grp_permission"]))
    EXP_MISCONFIGURED_GRP_NESTING.clear()
    EXP_MISCONFIGURED_GRP_NESTING.update(copy.deepcopy(snapshot["misconfig_grp_nesting"]))
    EXP_MISCONFIGURED_SESSION_USERS[:] = copy.deepcopy(snapshot["misconfig_session_users"])
    EXP_MISCONFIGURED_SESSION_COMPUTERS[:] = copy.deepcopy(snapshot["misconfig_session_computers"])
    EXP_MISCONFIGURED_PERMISSION_USERS[:] = copy.deepcopy(snapshot["misconfig_permissions_users"])
    EXP_MISCONFIGURED_PERMISSION_COMPUTERS[:] = copy.deepcopy(snapshot["misconfig_permissions_computers"])

    global EXP_neo4j_id
    EXP_neo4j_id = snapshot["neo4j_id"]

    if verbose:
        print(f"Restored experiment state for iteration {iteration_index}")
        print(f"Nodes: {len(EXP_NODES)}")
        print(f"Edges: {len(EXP_EDGES)}")
        print(f"Security Groups: {len(EXP_SECURITY_GROUPS)}")

    return {
        "iteration": iteration_index,
        "nodes": len(EXP_NODES),
        "edges": len(EXP_EDGES),
        "security_groups": len(EXP_SECURITY_GROUPS),
        "neo4j_id": EXP_neo4j_id,
    }


def _json_safe(obj: Any) -> Any:
    """Recursively convert non-JSON-native types to JSON-safe forms."""
    if isinstance(obj, dict):
        return {str(k): _json_safe(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_json_safe(v) for v in obj]
    if isinstance(obj, set):
        return sorted([_json_safe(v) for v in obj])  # stable output
    # Add more conversions here if needed (e.g., bytes -> base64)
    return obj

def _atomic_write_text(path: Path, text: str, compress: bool = False) -> None:
    """Write text atomically; supports gzip when compress=True."""
    path = Path(path)
    tmp = path.with_suffix(path.suffix + ".tmp")
    if compress:
        with gzip.open(tmp, "wt", encoding="utf-8") as f:
            f.write(text)
    else:
        with open(tmp, "w", encoding="utf-8") as f:
            f.write(text)
    os.replace(tmp, path)

def _read_text(path: Path) -> str:
    path = Path(path)
    if path.suffix.endswith(".gz"):
        with gzip.open(path, "rt", encoding="utf-8") as f:
            return f.read()
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def save_all_experiment_states_to_json(filepath: str, pretty: bool = True, compress: bool = False):
    """
    Serialize the entire EXPERIMENT_STATES dict to JSON (optionally .gz).
    Keys are converted to strings on write and restored to ints on load.
    """
    global EXPERIMENT_STATES
    data = {
        "meta": {
            "version": 1,
            "snapshots": len(EXPERIMENT_STATES),
        },
        "states": _json_safe(EXPERIMENT_STATES),  # make JSON-safe
    }
    kwargs = dict(indent=2, sort_keys=True) if pretty else dict(separators=(",", ":"), sort_keys=True)
    text = json.dumps(data, **kwargs)
    _atomic_write_text(Path(filepath), text, compress=compress)

def load_all_experiment_states_from_json(filepath: str, verbose: bool = False):
    """
    Load JSON into EXPERIMENT_STATES. Restores top-level keys to int.
    Does not mutate other globals; use restore_experiment_state() for that.
    """
    global EXPERIMENT_STATES
    text = _read_text(Path(filepath))
    loaded = json.loads(text)

    if "states" not in loaded or not isinstance(loaded["states"], dict):
        raise ValueError("Invalid snapshot file: missing 'states' dict")

    # Convert top-level keys back to ints where possible
    restored: Dict[int, Dict[str, Any]] = {}
    for k, v in loaded["states"].items():
        try:
            ik = int(k)
        except (ValueError, TypeError):
            # Fallback: keep as string if not an int
            ik = k
        restored[ik] = v

    EXPERIMENT_STATES = restored

    if verbose:
        print(f"Loaded {len(EXPERIMENT_STATES)} experiment snapshots from {filepath}")

    return {"snapshots": len(EXPERIMENT_STATES)}

def save_iteration_state_to_json(iteration_index: int, filepath: str, pretty: bool = True, compress: bool = False):
    """
    Save just one iteration snapshot (EXPERIMENT_STATES[iteration_index]) to JSON.
    Useful for per-iteration artifacts and diffing.
    """
    global EXPERIMENT_STATES
    if iteration_index not in EXPERIMENT_STATES:
        raise KeyError(f"No saved experiment state found for iteration {iteration_index}")

    data = {
        "meta": {"version": 1, "iteration": iteration_index},
        "state": _json_safe(EXPERIMENT_STATES[iteration_index]),
    }
    kwargs = dict(indent=2, sort_keys=True) if pretty else dict(separators=(",", ":"), sort_keys=True)
    text = json.dumps(data, **kwargs)
    _atomic_write_text(Path(filepath), text, compress=compress)

def load_iteration_state_from_json(filepath: str, iteration_index: int = None, verbose: bool = False):
    """
    Load a single iteration snapshot JSON and store it into EXPERIMENT_STATES[iteration_index].
    If iteration_index is None, tries to read from file meta.iteration.
    """
    global EXPERIMENT_STATES
    text = _read_text(Path(filepath))
    loaded = json.loads(text)

    if "state" not in loaded:
        raise ValueError("Invalid snapshot file: missing 'state' object")

    if iteration_index is None:
        iteration_index = loaded.get("meta", {}).get("iteration")
        if iteration_index is None:
            raise ValueError("iteration_index not provided and not found in file meta")

    EXPERIMENT_STATES[iteration_index] = loaded["state"]

    if verbose:
        print(f"Loaded snapshot for iteration {iteration_index} from {filepath}")

    return {"iteration": iteration_index}


def clear_exp_neo4j_db(session):
    total = 1
    while total > 0:
        result = session.run(
            "MATCH (n) WITH n LIMIT 10000 DETACH DELETE n RETURN count(n)")
        for r in result:
            total = int(r['count(n)'])

    remove_exp_neo4j_constraints(session)


def remove_exp_neo4j_constraints(session):
    # Remove constraint - From DBCreator
    print("Resetting Schema")
    for constraint in session.run("SHOW CONSTRAINTS"):
        session.run("DROP CONSTRAINT {}".format(constraint['name']))

    icount = session.run(
        "SHOW INDEXES YIELD name RETURN count(*)")
    for r in icount:
        ic = int(r['count(*)'])

    while ic > 0:
        print("Deleting indices from database")

        showall = session.run(
            "SHOW INDEXES")
        for record in showall:
            name = (record['name'])
            session.run("DROP INDEX {}".format(name))
        ic = 0

    # Setting constraints
    print("Setting constraints")

    constraints = [
        "CREATE CONSTRAINT FOR (n:Base) REQUIRE n.neo4jImportId IS UNIQUE;",
        "CREATE CONSTRAINT FOR (n:Domain) REQUIRE n.neo4jImportId IS UNIQUE;",
        "CREATE CONSTRAINT FOR (n:Computer) REQUIRE n.neo4jImportId IS UNIQUE;",
        "CREATE CONSTRAINT FOR (n:User) REQUIRE n.neo4jImportId IS UNIQUE;",
        "CREATE CONSTRAINT FOR (n:OU) REQUIRE n.neo4jImportId IS UNIQUE;",
        "CREATE CONSTRAINT FOR (n:GPO) REQUIRE n.neo4jImportId IS UNIQUE;",
        "CREATE CONSTRAINT FOR (n:Compromised) REQUIRE n.neo4jImportId IS UNIQUE;",
        "CREATE CONSTRAINT FOR (n:Group) REQUIRE n.neo4jImportId IS UNIQUE;",
        "CREATE CONSTRAINT FOR (n:Container) REQUIRE n.neo4jImportId IS UNIQUE;",
    ]

    for constraint in constraints:
        try:
            session.run(constraint)
        except:
            continue

    session.run("match (a) -[r] -> () delete a, r")
    session.run("match (a) delete a")


def update_graph_db_with_temp_file(session, operation):
    # print("Dump to JSON temp file")
    current_datetime = datetime.now()
    filename_suffix = current_datetime.strftime("%Y-%m-%d_%H-%M-%S-%f")[:-3]

    # Create a temporary file with delete=False so APOC can read it
    with tempfile.NamedTemporaryFile(
            mode="w", suffix=f"-{operation}.json", prefix=filename_suffix, dir=".", delete=False
    ) as tmpfile:
        temp_path = tmpfile.name

        # Write nodes
        for obj in EXP_NODES:
            obj["type"] = "node"
            json_str = json.dumps(obj, separators=(',', ':'))
            tmpfile.write(json_str + '\n')

        # Write edges
        for obj in EXP_EDGES:
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


import json
import os


def load_graph_from_file(session,filename: str):


    # file_path = f"/Users/yagzanmanjunaath/UniWorkspace/ResearchMethods/Part2/ADSynth/generated_datasets/{filename}"

    if not os.path.exists(filename):
        raise FileNotFoundError(f"File not found: {filename}")

    nodes, edges = [], []

    with open(filename, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError as e:
                print(f"Skipping invalid JSON line: {e}")
                continue

            if obj.get("type") == "node":
                # Remove "type" for clean in-memory representation
                obj.pop("type", None)
                nodes.append(obj)
            else:
                edges.append(obj)
    with tempfile.NamedTemporaryFile(
            mode="w", suffix=f"test.json",  dir=".", delete=False
    ) as tmpfile:
        temp_path = tmpfile.name


        for obj in nodes:
            obj["type"] = "node"
            json_str = json.dumps(obj, separators=(',', ':'))
            tmpfile.write(json_str + '\n')


        for obj in edges:
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


    print(f"Loaded {len(nodes)} nodes and {len(edges)} edges from {filename}")
    return {"nodes": len(nodes), "edges": len(edges), "path": filename}
