import copy
import sys
import warnings

def update_EXP_DATABASE_ID(label, EXP_NODES_index):
    identifiers = ["name", "objectid"]
    for identifier in identifiers:
        if identifier in EXP_NODES[EXP_NODES_index]["properties"]:
            check_data = EXP_NODES[EXP_NODES_index]["properties"][identifier]
            if identifier == "name":
                check_data += "_" + label

            if check_data not in EXP_DATABASE_ID[identifier]:
                EXP_DATABASE_ID[identifier][check_data] = EXP_NODES_index


def exp_node_operation(label, keys, values, id_lookup, identifier="objectid", is_domain=False):
    global EXP_neo4j_id
    EXP_NODES_index = -1
    new_node = dict()

    if identifier == "name":
        id_lookup += "_" + label


    if id_lookup in EXP_DATABASE_ID[identifier]:
        EXP_NODES_index = EXP_DATABASE_ID[identifier][id_lookup]
    else:
        new_node = copy.deepcopy(EXP_AD_NODE_ADMIN if is_domain else EXP_AD_NODE)

        EXP_NODES_index = len(EXP_NODES)
        EXP_NODES.append(new_node)
        EXP_DATABASE_ID[identifier][id_lookup] = EXP_NODES_index
        EXP_NODE_GROUPS[label].append(EXP_NODES_index)
        EXP_NODES[EXP_NODES_index]["id"] = str(EXP_neo4j_id)
        EXP_neo4j_id += 1

    for i in range(len(keys)):
        if keys[i] == "labels":
            if values[i] not in EXP_NODES[EXP_NODES_index][keys[i]]:
                EXP_NODES[EXP_NODES_index][keys[i]].append(values[i])
        else:
            EXP_NODES[EXP_NODES_index]["properties"][keys[i]] = values[i]

    if label in ("User", "Computer"):
        EXP_NODES[EXP_NODES_index]["properties"]["owned"] = False

    update_EXP_DATABASE_ID(label, EXP_NODES_index)
    return EXP_NODES_index


def exp_edge_operation(start_index, end_index, relationship_type, props=[], values=[]):
    hashed_id_edge = f"{start_index}{relationship_type}{end_index}"
    EXP_EDGES_index = -1
    new_edge = dict()

    if hashed_id_edge not in EXP_dict_edges:
        new_edge = copy.deepcopy(EXP_AD_EDGE)
        EXP_EDGES_index = len(EXP_EDGES)
        EXP_EDGES.append(new_edge)
        EXP_dict_edges[hashed_id_edge] = EXP_EDGES_index

        EXP_EDGES[EXP_EDGES_index]["id"] = f"r_{EXP_EDGES_index}"
        EXP_EDGES[EXP_EDGES_index]["label"] = relationship_type
        EXP_EDGES[EXP_EDGES_index]["start"]["id"] = EXP_NODES[start_index]["id"]
        EXP_EDGES[EXP_EDGES_index]["start"]["labels"] = EXP_NODES[start_index]["labels"]
        EXP_EDGES[EXP_EDGES_index]["end"]["id"] = EXP_NODES[end_index]["id"]
        EXP_EDGES[EXP_EDGES_index]["end"]["labels"] = EXP_NODES[end_index]["labels"]

        if EXP_NODES[start_index]["labels"][-1] == "GPO" and EXP_NODES[end_index]["labels"][-1] == "OU":
            EXP_GPLINK_OUS.append(end_index)
    else:
        EXP_EDGES_index = EXP_dict_edges[hashed_id_edge]

    for i in range(len(props)):
        EXP_EDGES[EXP_EDGES_index]["properties"][props[i]] = values[i]


def get_EXP_node_index(id_lookup, identifier):
    if id_lookup in EXP_DATABASE_ID[identifier]:
        return EXP_DATABASE_ID[identifier][id_lookup]
    warnings.simplefilter("error", UserWarning)
    warnings.warn(f"Node not exist: {id_lookup} - {identifier}")
    return -1



EXP_NODES = []
EXP_EDGES = []
EXP_neo4j_id = 0

EXP_DATABASE_ID = {
    "name": dict(),
    "objectid": dict()
}

EXP_dict_edges = dict()

EXP_AD_NODE = {
    "id": "",
    "labels": ["Base"],
    "properties": {}
}

EXP_AD_NODE_ADMIN = {
    "id": "",
    "labels": [],
    "properties": {}
}

EXP_AD_EDGE = {
    "type": "relationship",
    "id": "",
    "properties": {},
    "start": {},
    "end": {}
}

EXP_NODE_GROUPS = {
    "User": list(),
    "Computer": list(),
    "GPO": list(),
    "Group": list(),
    "Domain": list(),
    "OU": list(),
    "Container": list(),
}

EXP_GPLINK_OUS = []
EXP_GROUP_MEMBERS = dict()

EXP_SECURITY_GROUPS = []
EXP_ADMIN_USERS = []
EXP_ENABLED_USERS = []
EXP_DISABLED_USERS = []
EXP_PAW_TIERS = []
EXP_S_TIERS = []
EXP_S_TIERS_LOCATIONS = []
EXP_WS_TIERS = []
EXP_WS_TIERS_LOCATIONS = []
EXP_COMPUTERS = []
EXP_ridcount = []
EXP_KERBEROASTABLES = []
EXP_FOLDERS = []
EXP_DISTRIBUTION_GROUPS = []
EXP_SEC_DIST_GROUPS = []
EXP_LOCAL_ADMINS = []

# Misconfiguration tracking
EXP_MISCONFIGURED_SESSION_COMPUTERS = []
EXP_MISCONFIGURED_SESSION_USERS = []
EXP_MISCONFIGURED_SESSION = {}

EXP_MISCONFIGURED_PERMISSION_COMPUTERS = []
EXP_MISCONFIGURED_PERMISSION_USERS = []
EXP_MISCONFIGURED_PERMISSION = {}

EXP_MISCONFIGURED_GRP_PERMISSION = {}

EXP_MISCONFIGURED_GRP_NESTING = {}

