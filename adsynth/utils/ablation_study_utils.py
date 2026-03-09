import re

from adsynth.DATABASE import NODES
from adsynth.EXPERIMENT_DATABASE import EXP_EDGES

from collections import Counter

def get_baseline_from_AD(misconfig_type):

    if misconfig_type == "session":
            baseline_has_session = sum(1 for edge in EXP_EDGES if edge.get("label") == "HasSession")
            return  baseline_has_session


def tier_fn(node_name_or_id: str, labels=()) -> int:

    s = next((x for x in NODES if x["id"] == node_name_or_id), None)

    if s.startswith("PAW-"):
        return 0
    if s.startswith("S-"):
        return 1
    if s.startswith("WS-"):
        return 2
    return 2


def tier_from_dn(dn: str):
    if not dn:
        return None
    m = re.search(r"OU=T(\d+)\b", dn, flags=re.IGNORECASE)
    return int(m.group(1)) if m else 2

def indicators_hci_csm_tbs(EXP_EDGE,  low_tiers={2}, eps=1.0):
    has_Session_edge_count = [e for e in EXP_EDGE if e.get("label") == "HasSession"]


    d_sess = Counter(str(e["start"]["id"]) for e in has_Session_edge_count)

    C_low = {c for c in d_sess.keys() if tier_fn(c) in low_tiers}


    if not C_low:
        HCI = 0.0
    else:
        dbar = sum(d_sess[c] for c in C_low) / len(C_low)
        denom = (dbar + eps) ** 2
        HCI = (1 / len(C_low)) * sum((d_sess[c] ** 2) / denom for c in C_low)

    U = {str(e["end"]["id"]) for e in has_Session_edge_count}

    cross = 0
    t0_cross = 0
    U_T0 = set()

    for e in has_Session_edge_count:
        c = str(e["start"]["id"])
        u = str(e["end"]["id"])
        t_c = tier_fn(c)
        t_u = tier_from_dn(u)
        if t_u == 0:
            U_T0.add(u)

        if t_u < t_c:
            cross += 1
            if t_u == 0 and t_c > 0:
                t0_cross += 1

    CSM = cross / len(U) if U else 0.0
    TBS = t0_cross / len(U_T0) if U_T0 else 0.0

    return {"HCI": HCI, "CSM": CSM, "TBS": TBS}


def exposure_X(reachable_users_count, reachable_comps_count, num_users, num_computers):
    denom = num_users + num_computers
    return (reachable_users_count + reachable_comps_count) / denom if denom else 0.0

def exposure_parts(reachable_users_count, reachable_comps_count, num_users, num_computers):
    Xu = reachable_users_count / num_users if num_users else 0.0
    Xc = reachable_comps_count / num_computers if num_computers else 0.0
    return Xu, Xc

def exposure_per_baseline_session(X, N_baseline_session):
    return X / N_baseline_session if N_baseline_session else 0.0


def pbcc(L=6):
#     S - Reference set -> Tier 2 ws or printers
    pass
