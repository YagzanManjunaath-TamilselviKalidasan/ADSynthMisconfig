import copy
from adsynth.DATABASE import *
from adsynth.EXPERIMENT_DATABASE import *


def init_experiment_state(verbose: bool = True):
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
    EXP_MISCONFIGURED_SESSION_USERS[:] =[]
    EXP_MISCONFIGURED_SESSION.clear()

    EXP_MISCONFIGURED_PERMISSION_COMPUTERS[:] = []
    EXP_MISCONFIGURED_PERMISSION_USERS[:] = []
    EXP_MISCONFIGURED_PERMISSION.clear()


    global EXP_neo4j_id
    EXP_neo4j_id = neo4j_id

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
