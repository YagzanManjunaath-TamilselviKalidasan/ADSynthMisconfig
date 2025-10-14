from adsynth.DATABASE import ADMIN_USERS, ENABLED_USERS, LOCAL_ADMINS, PAW_TIERS, S_TIERS, SECURITY_GROUPS, WS_TIERS, \
    edge_operation, get_node_index
from adsynth.EXPERIMENT_DATABASE import EXP_ADMIN_USERS, EXP_ENABLED_USERS, EXP_PAW_TIERS, EXP_S_TIERS, EXP_WS_TIERS, \
    EXP_MISCONFIGURED_SESSION_COMPUTERS, EXP_MISCONFIGURED_SESSION_USERS, exp_edge_operation, EXP_MISCONFIGURED_SESSION, \
    EXP_MISCONFIGURED_PERMISSION_COMPUTERS, EXP_MISCONFIGURED_PERMISSION_USERS, EXP_MISCONFIGURED_PERMISSION, \
    get_EXP_node_index
from adsynth.adsynth_templates.admin_groups import get_admin_groups
from adsynth.adsynth_templates.permissions import get_non_acls_list
from adsynth.entities.acls import cn
from adsynth.helpers.getters import get_locations, get_misconfig_dict_param_value
from adsynth.templates.acls import get_acls_list
from adsynth.templates.groups import get_departments_list
from adsynth.utils.networkx_utils import get_id_from_name, create_networkx_graph
from adsynth.utils.parameters import get_dict_param_value, get_int_param_value, get_perc_param_value
import random




def create_misconfig_sessions_multi_tiers(nTiers, num_users, security_level, parameters):
    if nTiers < 2:
        pass

    perc_misconfig_sessions = get_perc_param_value("perc_misconfig_sessions", security_level, parameters) / 100
    num_misconfig = int(perc_misconfig_sessions * num_users)

    for i in range(num_misconfig):
        is_admin = random.choice([True, False])

        # Specify the user' tier
        ut = random.randrange(0, nTiers - 1)

        # Sample a user at the specified tier
        lowest_tier_no_admin = min(2, nTiers - 1)
        if is_admin or ut < lowest_tier_no_admin:
            user = random.choice(ADMIN_USERS[ut])
        else:
            try:
                user = random.choice(ENABLED_USERS[ut])
            except:
                continue

        # Determine computer's tier
        ct = random.randrange(ut + 1, nTiers)

        # Sample a computer
        if ct == 0:  # PAW
            comp = random.choice(PAW_TIERS[0])
        elif ct == 1 and nTiers > 2:  # Servers
            comp = random.choice(PAW_TIERS[ct] + S_TIERS[ct])
        else:  # Workstations
            comp = random.choice(PAW_TIERS[ct] + S_TIERS[ct] + WS_TIERS[ct])

        # Generate a session
        start_index = get_node_index(comp + "_Computer", "name")
        end_index = get_node_index(user + "_User", "name")
        edge_operation(start_index, end_index, "HasSession")


def create_misconfig_sessions_no_tier(nTiers, num_users, security_level, parameters):
    if nTiers > 1:
        return

    # From admins to workstations and servers (excluding T1 servers)
    perc_misconfig_sessions = get_perc_param_value("perc_misconfig_sessions", security_level, parameters) / 100
    num_misconfig = int(perc_misconfig_sessions * num_users)

    for i in range(num_misconfig):
        # Sample an admin user
        user = random.choice(ADMIN_USERS[0])

        # Sample a workstation or a server
        try:
            comp = random.choice(S_TIERS[0] + WS_TIERS[0])
        except:
            continue

        # Generate a session
        start_index = get_node_index(comp + "_Computer", "name")
        end_index = get_node_index(user + "_User", "name")
        edge_operation(start_index, end_index, "HasSession")


def create_misconfig_sessions(nTiers, security_level, parameters, num_users):
    if nTiers == 1:
        create_misconfig_sessions_no_tier(nTiers, num_users, security_level, parameters)
    else:
        create_misconfig_sessions_multi_tiers(nTiers, num_users, security_level, parameters)


def create_misconfig_permissions_on_individuals(nTiers, A, EU, security_level, parameters, num_users):
    if nTiers == 1:
        return
    CP = ["AdminTo", "CanRDP", "CanPSRemote", "ExecuteDCOM", "AllowedToDelegate", "ReadLAPSPassword", "SQLAdmin",
          "AllowedToAct"]
    misconfig_perc = get_perc_param_value("perc_misconfig_permissions", security_level, parameters) / 100
    num_misconfig = int(misconfig_perc * num_users)

    misconfig_to_tier_0_allow, misconfig_to_tier_0_limit = get_misconfig_dict_param_value(
        "misconfig_permissions_to_tier_0", parameters)

    for i in range(num_misconfig):
        # Specify the user' tier
        lowest_tier_no_admin = min(2, nTiers - 1)
        ut = random.randrange(lowest_tier_no_admin, nTiers)

        # Sample a user at the specified tier
        try:
            user = random.choice(EU[ut])
        except:
            continue

        # Determine computer's tier
        if nTiers < 2:
            ct = 0
        else:
            if misconfig_to_tier_0_allow:
                if misconfig_to_tier_0_limit < 0 or misconfig_to_tier_0_limit > 0:
                    ct = random.randrange(0, ut)
                    misconfig_to_tier_0_limit -= 1
                else:
                    try:
                        ct = random.randrange(1, ut)
                    except:
                        continue
            else:
                try:
                    ct = random.randrange(1, ut)
                except:
                    continue

        # Sample a computer
        if ct == 0:  # PAW
            comp = random.choice(PAW_TIERS[0])
        elif ct == 1 and nTiers > 2:  # Servers
            comp = random.choice(PAW_TIERS[ct] + S_TIERS[ct])
        else:  # Workstations
            comp = random.choice(PAW_TIERS[ct] + S_TIERS[ct] + WS_TIERS[ct])

        # Generate a session
        start_index = get_node_index(user + "_User", "name")
        end_index = get_node_index(comp + "_Computer", "name")
        rel_type = random.choice(CP)
        edge_operation(start_index, end_index, rel_type)


def create_misconfig_permissions_on_groups(domain, nTiers, security_level, parameters, num_groups):
    # 2 lists for ACL and non-ACL permissions
    # ACLs
    acl_permission_probs = get_dict_param_value("ACLs", "ACLsProbability", parameters)
    ACL_PERMISSIONS = get_acls_list(acl_permission_probs)

    # Non-ACLs
    non_acl_permission_probs = get_dict_param_value("nonACLs", "nonACLsProbability", parameters)
    NON_ACL_PERMISSIONS = get_non_acls_list(non_acl_permission_probs)

    # Retrieve the number of misconfig
    misconfig_perc = get_perc_param_value("perc_misconfig_permissions_on_groups", security_level, parameters) / 100
    num_misconfig = int(misconfig_perc * num_groups)

    # Establish the limit to attack Tier 0 for non_ACL permissions
    misconfig_to_tier_0_allow, misconfig_to_tier_0_limit = get_misconfig_dict_param_value(
        "misconfig_permissions_to_tier_0", parameters)

    # ACL setup
    acl_ratio = get_perc_param_value("misconfig_group", "acl_ratio", parameters)
    admin_ratio = get_perc_param_value("misconfig_group", "admin_ratio", parameters)
    departments_probs = get_dict_param_value("Group", "departmentProbability", parameters)
    departments_list = get_departments_list(departments_probs)
    locations = get_locations(parameters)

    # For loop to generate misconfig
    for i in range(num_misconfig):
        # Determine a group (LOCAL ADMINS)
        lowest_tier_no_admin = min(2, nTiers - 1)
        group_tier = random.randrange(lowest_tier_no_admin, nTiers)
        try:
            group_name = random.choice(LOCAL_ADMINS[group_tier])
        except:
            continue

        # Sample a permissions ACL/non-ACL
        is_acl = random.choice([True] * acl_ratio + [False] * (100 - acl_ratio))
        if not is_acl:
            rel_type = random.choice(NON_ACL_PERMISSIONS)

            # Determine OU tier
            if nTiers < 2:
                ou_tier = 0
            else:
                if misconfig_to_tier_0_allow:
                    if misconfig_to_tier_0_limit < 0 or misconfig_to_tier_0_limit > 0:
                        ou_tier = random.randrange(0, group_tier)
                        misconfig_to_tier_0_limit -= 1
                    else:
                        ou_tier = random.randrange(1, group_tier)
                else:
                    ou_tier = random.randrange(1, group_tier)
            target_ou_name = f"T{ou_tier} Admin Devices"
        else:
            rel_type = random.choice(ACL_PERMISSIONS)

            # Determine admin/non-admin target
            is_admin = True
            if group_tier > 2:
                is_admin = random.choice([True] * admin_ratio + [False] * (100 - admin_ratio))

            if is_admin:
                if nTiers < 2:
                    ou_tier = 0
                else:
                    ou_tier = random.randrange(0, group_tier + 1)

                priority_paws_weight = get_int_param_value("misconfig_group", "priority_paws_weight", parameters)
                weights = [1 for i in range(4)]
                weights[-1] = priority_paws_weight
                potential_ous = [f"T{ou_tier} Admin Accounts", f"T{ou_tier} Admin Groups",
                                 f"T{ou_tier} Admin Service Accounts", f"T{ou_tier} Admin Devices"]
                target_ou_name = random.choices(potential_ous, weights)[0]
            else:
                ou_tier = random.randrange(lowest_tier_no_admin, group_tier)

                # OU_TYPES 
                # 0: Users
                # 1: Workstations
                # 2: Servers
                # 3: Group
                ou_types = random.choice(range(4))

                if ou_types == 0:
                    target_ou_name = f"T{ou_tier} Enabled User Accounts"
                else:
                    if ou_types > 2:
                        group_type = random.choice(["Distribution", "Security"])
                        dept = random.choice(departments_list)
                        target_ou_name = f"T{ou_tier} {group_type} {dept}"
                    else:
                        l = random.choice(locations)
                        computer_type = random.choice(["Workstations", "Servers"])
                        target_ou_name = f"T{ou_tier} {computer_type} {l}"

        start_index = get_node_index(cn(group_name, domain) + "_Group", "name")
        end_index = get_node_index(cn(target_ou_name, domain) + "_OU", "name")
        edge_operation(start_index, end_index, rel_type)


def create_misconfig_group_nesting(domain, nTiers, security_level, parameters, num_groups):
    misconfig_perc = get_perc_param_value("perc_misconfig_nesting_groups", security_level, parameters) / 100
    num_misconfig = int(misconfig_perc * num_groups)

    # Departments and locations
    departments_probs = get_dict_param_value("Group", "departmentProbability", parameters)
    departments_list = get_departments_list(departments_probs)
    locations = get_locations(parameters)

    for i in range(num_misconfig):
        # Determine a non-admin/regular group
        # Choose a tier and group type
        lowest_tier_no_admin = min(2, nTiers - 1)
        regular_group_tier = random.randrange(lowest_tier_no_admin, nTiers)
        group_type = random.choice(["Distribution", "Security"])
        if group_type == "Distribution":
            d = random.choice(departments_list)
            l = random.choice(locations)
            regular_group_name = cn(f"T{regular_group_tier} Distribution {d}_{l}", domain)
        else:
            regular_group_name = random.choice(SECURITY_GROUPS[regular_group_tier])

        # Determine a target admin group
        target_group_tier = random.randrange(0, regular_group_tier + 1)
        target_group_name = random.choice(get_admin_groups(target_group_tier))

        # Nest regular groups in admin groups
        start_index = get_node_index(regular_group_name + "_Group", "name")
        end_index = get_node_index(cn(target_group_name, domain) + "_Group", "name")
        edge_operation(start_index, end_index, "MemberOf")


##
# Assumption : Low tier computer is considered as a entry point and We check for path from this computer to domain admin
# Same user - Based on edge from Computer to domain is chosen and msiconfiguration is injected

##
# Check hasSession computer -> users are entry points  : Check path to domain admin
#
#
##
def create_misconfig_sessions_from_entrypoints_multi_tiers(nTiers, nx_attack_graph, security_level, parameters):
    if nTiers < 2:
        pass

    is_admin = random.choice([True, False])
    retry_count = 0
    while retry_count < 3:
        # Specify the user' tier
        ut = random.randrange(0, nTiers - 1)

        # Sample a user at the specified tier
        lowest_tier_no_admin = min(2, nTiers - 1)
        if is_admin or ut < lowest_tier_no_admin:
            user = random.choice(EXP_ADMIN_USERS[ut])
        else:
            try:
                user = random.choice(EXP_ENABLED_USERS[ut])
            except:
                print(f"Retry {retry_count}")
                retry_count = retry_count + 1
        # Determine computer's tier
        ct = random.randrange(ut + 1, nTiers)

        # Sample a computer
        if ct == 0:  # PAW
            comp = random.choice(EXP_PAW_TIERS[0])
        elif ct == 1 and nTiers > 2:  # Servers
            comp = random.choice(EXP_PAW_TIERS[ct] + EXP_S_TIERS[ct])
        else:  # Workstations
            comp = random.choice(EXP_PAW_TIERS[ct] + EXP_S_TIERS[ct] + EXP_WS_TIERS[ct])

        if comp in EXP_MISCONFIGURED_SESSION_COMPUTERS and user in EXP_MISCONFIGURED_SESSION_USERS:
            retry_count = retry_count + 1
            continue
        # Generate a session
        start_index = get_EXP_node_index(comp + "_Computer", "name")
        end_index = get_EXP_node_index(user + "_User", "name")
        exp_edge_operation(start_index, end_index, "HasSession")

        nx_attack_graph = create_networkx_graph()
        # nx_start_id = get_id_from_name(nx_attack_graph, comp)
        # nx_end_id = get_id_from_name(nx_attack_graph, user)

        # nx_attack_graph.add_edge(nx_start_id, nx_end_id, method="HasSession")

        EXP_MISCONFIGURED_SESSION_COMPUTERS.append(comp)
        EXP_MISCONFIGURED_SESSION_USERS.append(user)
        EXP_MISCONFIGURED_SESSION[comp] = user
        break
    return nx_attack_graph
    # todo - Use HasSession to do simulate similar admin user to log into lower tier computer
    # print("Misconfigured Sessions")
    # print(MISCONFIGURED_SESSION)


def create_misconfig_permissions_on_individuals_from_entrypoints(nTiers, EXP_ADMIN_USERS, EXP_ENABLED_USERS, security_level, parameters, num_users,nx_attack_graph ):
    if nTiers == 1:
        return
    CP = ["AdminTo", "CanRDP", "CanPSRemote", "ExecuteDCOM", "AllowedToDelegate", "ReadLAPSPassword", "SQLAdmin",
          "AllowedToAct"]
    misconfig_perc = get_perc_param_value("perc_misconfig_permissions", security_level, parameters) / 100
    num_misconfig = int(misconfig_perc * num_users)

    misconfig_to_tier_0_allow, misconfig_to_tier_0_limit = get_misconfig_dict_param_value(
        "misconfig_permissions_to_tier_0", parameters)
    # print("Misconfig" ,num_misconfig)

    # Specify the user' tier
    lowest_tier_no_admin = min(2, nTiers - 1)
    ut = random.randrange(lowest_tier_no_admin, nTiers)

    # Sample a user at the specified tier

    user = random.choice(EXP_ENABLED_USERS[ut])

    # Determine computer's tier
    if nTiers < 2:
        ct = 0
    else:
        if misconfig_to_tier_0_allow:
            if misconfig_to_tier_0_limit < 0 or misconfig_to_tier_0_limit > 0:
                ct = random.randrange(0, ut)
                misconfig_to_tier_0_limit -= 1
            else:

                ct = random.randrange(1, ut)

        else:

            ct = random.randrange(1, ut)

        # Sample a computer
        if ct == 0:  # PAW
            comp = random.choice(EXP_PAW_TIERS[0])
        elif ct == 1 and nTiers > 2:  # Servers
            comp = random.choice(EXP_PAW_TIERS[ct] + EXP_S_TIERS[ct])
        else:  # Workstations
            comp = random.choice(EXP_PAW_TIERS[ct] + EXP_S_TIERS[ct] + EXP_WS_TIERS[ct])

        start_index = get_EXP_node_index(user + "_User", "name")
        end_index = get_EXP_node_index(comp + "_Computer", "name")
        rel_type = random.choice(CP)
        exp_edge_operation(start_index, end_index, rel_type)
        nx_attack_graph = create_networkx_graph()
        EXP_MISCONFIGURED_PERMISSION_COMPUTERS.append(comp)
        EXP_MISCONFIGURED_PERMISSION_USERS.append(user)

        EXP_MISCONFIGURED_PERMISSION[comp] = user + " "+rel_type

        print("Misconfigured Permissions")
        print(EXP_MISCONFIGURED_PERMISSION)
        return  nx_attack_graph


def create_misconfig_permissions_on_individuals_from_entrypoints_with_custom_graph(
        nTiers,
        A,
        EU,
        security_level,
        parameters,
        num_users,
        nx_attack_graph=None,
):
    """
    Create permission misconfigs by adding relationship edges from users -> computers.
    If nx_attack_graph is supplied, also add edges into that graph and return it.
    """
    if nTiers == 1:
        return nx_attack_graph

    CP = [
        "AdminTo",
        "CanRDP",
        "CanPSRemote",
        "ExecuteDCOM",
        "AllowedToDelegate",
        "ReadLAPSPassword",
        "SQLAdmin",
        "AllowedToAct",
    ]
    misconfig_perc = get_perc_param_value("perc_misconfig_permissions", security_level, parameters) / 100
    num_misconfig = int(misconfig_perc * num_users)

    misconfig_to_tier_0_allow, misconfig_to_tier_0_limit = get_misconfig_dict_param_value(
        "misconfig_permissions_to_tier_0", parameters
    )

    for i in range(num_misconfig):
        # pick a user tier (avoid admin-only tiers for sampling)
        lowest_tier_no_admin = min(2, nTiers - 1)
        ut = random.randrange(lowest_tier_no_admin, nTiers)

        # Sample a user at the specified tier
        try:
            user = random.choice(EU[ut])
        except Exception:
            # skip if no users available at that tier
            continue

        # Decide target computer tier
        if nTiers < 2:
            ct = 0
        else:
            # if allowed to misconfig to tier0, try to pick from 0..ut-1 respecting limit
            if misconfig_to_tier_0_allow:
                # if limit is negative treat as unlimited, otherwise decrement limit after use
                if misconfig_to_tier_0_limit < 0:
                    ct = random.randrange(0, ut)
                else:
                    # pick 0..ut-1 but ensure limit is honoured
                    if misconfig_to_tier_0_limit > 0:
                        ct = random.randrange(0, ut)
                        misconfig_to_tier_0_limit -= 1
                    else:
                        # limit exhausted: choose from 1..ut-1 if possible
                        try:
                            ct = random.randrange(1, ut)
                        except Exception:
                            continue
            else:
                try:
                    ct = random.randrange(1, ut)
                except Exception:
                    continue

        # Sample a computer from tier lists (fall back patterns preserved)
        try:
            if ct == 0:  # PAW
                comp = random.choice(EXP_PAW_TIERS[0])
            elif ct == 1 and nTiers > 2:  # Servers
                comp = random.choice(EXP_PAW_TIERS[ct] + EXP_S_TIERS[ct])
            else:  # Workstations or other tiers
                comp = random.choice(EXP_PAW_TIERS[ct] + EXP_S_TIERS[ct] + EXP_WS_TIERS[ct])
        except Exception:
            # if sampling failed, skip
            continue

        # create relationship
        rel_type = random.choice(CP)
        start_index = get_EXP_node_index(user + "_User", "name")
        end_index = get_EXP_node_index(comp + "_Computer", "name")

        # existing helper that likely updates DB/neo4j
        try:
            exp_edge_operation(start_index, end_index, rel_type)
        except Exception:
            # don't fail entirely if edge operation throws; continue but at least try to add to nx graph
            pass

        # update networkx graph if present
        if nx_attack_graph is not None:
            try:
                nx_start_id = get_id_from_name(nx_attack_graph, user + "_User")
                nx_end_id = get_id_from_name(nx_attack_graph, comp + "_Computer")
                # include rel_type as edge attribute
                nx_attack_graph.add_edge(nx_start_id, nx_end_id, method=rel_type)
            except Exception:
                # fallback: add nodes by name and connect (preserve minimal info)
                try:
                    nx_attack_graph.add_node(user + "_User", name=user + "_User")
                    nx_attack_graph.add_node(comp + "_Computer", name=comp + "_Computer")
                    nx_attack_graph.add_edge(user + "_User", comp + "_Computer", method=rel_type)
                except Exception:
                    pass

        # track for reporting / de-duplication (keeps old behavior)
        EXP_MISCONFIGURED_SESSION_COMPUTERS.append(comp)
        EXP_MISCONFIGURED_SESSION_USERS.append(user)
        EXP_MISCONFIGURED_SESSION[comp] = user

    # print summary (keeps original behavior)
    print("Misconfigured Sessions (permissions):")
    print(EXP_MISCONFIGURED_SESSION)

    return nx_attack_graph
