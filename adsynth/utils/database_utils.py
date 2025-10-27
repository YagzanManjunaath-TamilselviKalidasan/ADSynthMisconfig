import copy
import json
import os
import tempfile
from datetime import datetime

from adsynth.DATABASE import *
from adsynth.EXPERIMENT_DATABASE import *

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
