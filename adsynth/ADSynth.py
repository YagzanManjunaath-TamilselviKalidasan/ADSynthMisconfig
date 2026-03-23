# Requirements - pip install neo4j-driver
# This script is used to create randomized sample databases.
# Commands
# 	dbconfig - Set the credentials and URL for the database you're connecting too
#	connect - Connects to the database using supplied credentials
# 	setparams - Set the settings JSON file
# 	setdomain - Set the domain name
# 	cleardb - Clears the database and sets the schema properly
#	generate - Connects to the database, clears the DB, sets the schema, and generates random data

# from neo4j import GraphDatabase
import getpass
import cmd
import logging
from calendar import error
from scipy.stats import t
from collections import defaultdict
import uuid
import time
import random
import os
from pprint import pprint

import networkx
import numpy as np
from tabulate import tabulate
import pandas as pd
from IPython.display import display

from adsynth.EXPERIMENT_DATABASE import EXP_ADMIN_USERS, EXP_ENABLED_USERS, EXP_MISCONFIGURED_SESSION, EXP_LOCAL_ADMINS, \
    EXP_NODES, EXP_EDGES, EXP_MISCONFIGURED_GRP_PERMISSION, EXP_MISCONFIGURED_GRP_NESTING
from adsynth.adsynth_templates.permissions import get_non_acls_list
from adsynth.default_ad_system.default_acls import create_administrators_acls, create_default_AllExtendedRights, \
    create_default_GenericAll, create_default_GenericWrite, create_default_dc_groups_acls, create_default_groups_acls, \
    create_default_owns, create_default_users_acls, create_default_write_dacl_owner, create_domain_admins_acls, \
    create_enterprise_admins_acls
from adsynth.default_ad_system.default_gpos import apply_default_gpos, create_default_gpos
from adsynth.default_ad_system.default_groups import create_adminstrator_memberships, create_default_groups, \
    generate_default_member_of
from adsynth.default_ad_system.default_ous import create_domain_controllers_ou
from adsynth.default_ad_system.default_users import generate_administrator, generate_default_account, \
    generate_guest_user, generate_krbtgt_user, link_default_users_to_domain
from adsynth.default_ad_system.domains import create_domain
from adsynth.entities.acls import cs
from adsynth.helpers.about import print_adsynth_software_information
from adsynth.helpers.getters import get_num_tiers, get_single_int_param_value, get_misconfig_dict_param_value, \
    get_locations
from adsynth.helpers.objects import segregate_list
from adsynth.synthesizer.misconfig import create_misconfig_group_nesting, create_misconfig_permissions_on_groups, \
    create_misconfig_permissions_on_individuals, create_misconfig_sessions, \
    create_misconfig_sessions_from_entrypoints_multi_tiers, \
    create_misconfig_permissions_on_individuals_from_entrypoints, \
    create_misconfig_permissions_on_groups_from_entrypoints, create_misconfig_group_nesting_from_entrypoints
from adsynth.synthesizer.object_placement import nest_groups, place_admin_users_in_tiers, place_computers_in_tiers, \
    place_normal_users_in_tiers, place_users_in_groups
from adsynth.synthesizer.objects import create_admin_groups, create_groups, create_kerberoastable_users, \
    generate_computers, generate_dcs, generate_users
from adsynth.synthesizer.ou_structure import create_ad_skeleton
from adsynth.synthesizer.permissions import assign_administration_to_admin_principals, assign_local_admin_rights, \
    create_control_management_permissions
from adsynth.synthesizer.security_policies import apply_gpos, apply_restriction_gpos, create_gpos_container, \
    place_gpos_in_container
from adsynth.synthesizer.sessions import create_dc_sessions, create_sessions
from adsynth.templates.acls import get_acls_list
from adsynth.templates.groups import get_departments_list
from adsynth.utils.ablation_study_utils import get_baseline_from_AD, indicators_hci_csm_tbs, exposure_X, exposure_parts, \
    populate_node_tiers, pbcc_bounded_bfs_footholds, compute_mu, compute_sigma2, \
    compute_mu_sigma_ci, compute_delta_X, find_p_star, compute_hub_correlation
from adsynth.utils.data import get_names_pool, get_surnames_pool, get_parameters_from_json, get_domains_pool
from adsynth.utils.database_utils import init_experiment_state, restore_experiment_state, save_experiment_state, \
    clear_exp_neo4j_db, update_graph_db_with_temp_file, save_all_experiment_states_to_json, load_graph_from_file, \
    load_all_experiment_states_from_json
from adsynth.utils.domains import get_domain_dn
from adsynth.utils.parameters import print_all_parameters, get_int_param_value, get_perc_param_value, \
    get_dict_param_value
from adsynth.adsynth_templates.default_config import DEFAULT_CONFIGURATIONS
from adsynth.DATABASE import *
from adsynth.utils.misconfig_utils import update_db, check_shortest_paths_from_misconfigured_users_using_cypher, \
    export_user_level_data_to_csv, analyze_group_surges_from_csv, tabulate_experiment_results
from adsynth.utils.networkx_utils import create_networkx_graph, draw_graph, find_shortest_paths_from_misconfig_users, \
    calculate_total_paths_to_domain_admins, find_user_count_with_path_to_DA, find_user_count_with_path_to_DA_undirected, \
    find_user_count_with_path_to_DA_fast, create_networkx_graph_fast, create_igraph_from_adsynth, \
    find_user_count_with_path_to_DA_igraph
import json
from timeit import default_timer as timer
from datetime import datetime

from adsynth.utils.plot_utils import plot_plot_chart, plot_box_plot_using_plotty, plot_chart_using_plotly, plot_metrics
from adsynth.utils.prediction_utils import calc_thresholds_and_jump_labels


def delete_neo4j_data(session):
    try:
        query = '''
          MATCH (n)
        DETACH DELETE n
        '''
        print("Clearing conencted neo4j db")
        session.run(query)
    except Exception as e:
        print(f"Exception occurred while clearing Neo4j db {e}")


def reset_DB():
    NODES.clear()
    EDGES.clear()

    for item in DATABASE_ID:
        DATABASE_ID[item].clear()

    dict_edges.clear()

    for item in NODE_GROUPS:
        NODE_GROUPS[item].clear()

    GPLINK_OUS.clear()

    GROUP_MEMBERS.clear()

    SECURITY_GROUPS.clear()

    LOCAL_ADMINS.clear()

    ADMIN_USERS.clear()

    ENABLED_USERS.clear()  # processed names # Tiered

    DISABLED_USERS.clear()  # processed names

    PAW_TIERS.clear()  # Tiered

    S_TIERS.clear()  # Tiered

    WS_TIERS.clear()  # Tiered

    COMPUTERS.clear()  # All

    ridcount.clear()

    KERBEROASTABLES.clear()  # processed names


neo4j = None


def safe_import_neo4j():
    global neo4j
    try:
        import neo4j as neo4j_lib
        neo4j = neo4j_lib
        return neo4j
    except ImportError:
        print("The 'neo4j' module is not installed. Please install it using 'pip install -r requirements.txt'.")
        return None


class Messages():
    def title(self):
        print(
            """
                                                                           ,----,            
                                                               ,--.      ,/   .`|       ,--, 
       ,---,           ,---,      .--.--.                    ,--.'|    ,`   .'  :     ,--.'| 
      '  .' \        .'  .' `\   /  /    '.      ,---,   ,--,:  : |  ;    ;     /  ,--,  | : 
     /  ;    '.    ,---.'     \ |  :  /`. /     /_ ./|,`--.'`|  ' :.'___,/    ,',---.'|  : ' 
    :  :       \   |   |  .`\  |;  |  |--`,---, |  ' :|   :  :  | ||    :     | |   | : _' | 
    :  |   /\   \  :   : |  '  ||  :  ;_ /___/ \.  : |:   |   \ | :;    |.';  ; :   : |.'  | 
    |  :  ' ;.   : |   ' '  ;  : \  \    `.  \  \ ,' '|   : '  '; |`----'  |  | |   ' '  ; : 
    |  |  ;/  \   \|'   | ;  .  |  `----.   \  ;  `  ,''   ' ;.    ;    '   :  ; '   |  .'. | 
    '  :  | \  \ ,'|   | :  |  '  __ \  \  |\  \    ' |   | | \   |    |   |  ' |   | :  | ' 
    |  |  '  '--'  '   : | /  ;  /  /`--'  / '  \   | '   : |  ; .'    '   :  | '   : |  : ; 
    |  :  :        |   | '` ,/  '--'.     /   \  ;  ; |   | '`--'      ;   |.'  |   | '  ,/  
    |  | ,'        ;   :  .'      `--'---'     :  \  ||'   : |          '---'    ;   : ;--'   
    `--''          |   ,.'                      \  ' ;;   |.'                   |   ,/       
                   '---'                         `--` '---'                     '---'        
                                                                                             
                                                                                                                                                                                                  
            """
        )
        print("Synthesizing realisitc Active Directory attack graphs\n")
        print("==================================================================")

    # Ref: DBCreator
    def input_default(self, prompt, default):
        return input("%s [%s] " % (prompt, default)) or default

    def input_default_password(self, prompt, default, hide_input=False):
        if hide_input:
            # Use getpass to securely input passwords
            prompt_with_default = f"{prompt} [{default}] "
            return getpass.getpass(prompt_with_default) or default
        else:
            # Regular input for other types of data
            return input(f"{prompt} [{default}] ") or default

    def input_security_level(self, prompt, default):
        user_input = input("%s [%s] " % (prompt, default)) or default
        if not user_input:
            return default

        try:
            user_input = int(user_input)
            if user_input in [1, 2, 3]:
                return user_input
        except:
            pass
        return default

    # Ref: DBCreator
    def input_yesno(self, prompt, default):
        temp = input(prompt + " " + ("Y" if default else "y") + "/" + ("n" if default else "N") + " ")
        if temp == "y" or temp == "Y":
            return True
        elif temp == "n" or temp == "N":
            return False
        return default


class MainMenu(cmd.Cmd):
    # The main functions to generate realistic Active Directory attack graphs using metagraphs belong to ADSynth.
    # In case of code re-use from previous work, LICENSING is provided at the top of a file
    # In case of code modification or ideas related to fundamental concepts of Active Directory, clear references are mentioned at the top of such functions.

    def __init__(self):
        self.skip_plots = True
        self.m = Messages()
        self.url = "bolt://localhost:7687"
        self.username = "neo4j"
        self.password = "neo4j"
        self.use_encryption = False
        self.driver = None
        self.connected = False
        self.old_domain = None
        self.domain = "TESTLAB.LOCALE"
        self.current_time = int(time.time())
        self.base_sid = "S-1-5-21-883232822-274137685-4173207997"
        self.first_names = get_names_pool()
        self.last_names = get_surnames_pool()
        self.domain_names = get_domains_pool()
        self.parameters_json_path = "DEFAULT"
        self.parameters = DEFAULT_CONFIGURATIONS
        self.json_file_name = None
        self.level = "Customized"
        self.dbname = None
        self.misconfig_enabled = True
        # R realizations - iterations as of now
        self.R = 20
        cmd.Cmd.__init__(self)
        logging.basicConfig(
            filename="app.log",
            level=logging.INFO,
            format="%(message)s"
        )

    def cmdloop(self):
        while True:
            self.m.title()
            self.do_help("")
            try:
                try:
                    cmd.Cmd.cmdloop(self)
                except EOFError:
                    break
                    return True

            except KeyboardInterrupt:
                if self.driver is not None:
                    self.driver.close()
                return True

    def help_adconfig(self):
        print("Configure AD level of security")

    def help_neo4jconfig(self):
        print("Configure Neo4J database")

    def help_connect(self):
        print("Test connection to the database and verify credentials")

    def help_setdomain(self):
        print("Set domain name (default 'TESTLAB.LOCALE')")

    def help_cleardb(self):
        print("Clear the Neo4J database and set constraints")

    def help_generate(self):
        print("Generate an Active Directory attack graph based on the given parameters")

    def help_setparams(self):
        print("Import the settings JSON file containing the parameters for the graph generation")

    def help_about(self):
        print("View information about adsynth")

    def help_importdb(self):
        print("Import a JSON file to Neo4J")

    def help_inject_session_misconfigs(self):
        print("Inject and Check session misconfigurations")

    def help_inject_individual_permission_misconfigs(self):
        print("Inject and Check permission misconfigurations for users")

    def help_inject_group_permission_misconfigs(self):
        print("Inject and Check permission misconfigurations for groups")

    def help_initialise_1k_AD(self):
        print("Generate 1K Graph for misconfiguration")

    def help_initialise_AD_graph_from_json(self):
        print("Generate an Active Directory attack graph based on the given parameters")
        print("Pass json path of configuration as --json [path]")
        print("Pass Security level of configuration as --level [High/Low/Customized]")
        print("Sample command ")
        print("initialise_AD_graph_from_json --json secure_1k.json --level High")

    def help_exit(self):
        print("Exit")

    # def help_remove_constraints(self):
    #     print("Remove Neo4J constraints")

    def do_about(self, args):
        print_adsynth_software_information()

    def do_adconfig(self, args):
        # Level of security
        security_settings = {
            1: "Customized",
            2: "Low",
            3: "High"
        }
        security_settings_code = {
            "Customized": 1,
            "Low": 2,
            "High": 3
        }

        level_code = self.m.input_security_level(
            "Enter level of security  (type a number 1/2/3) - Cuztomized (1), Low (2), High (3): ",
            security_settings_code[self.level])
        self.level = security_settings[level_code]
        print("Level of Security: {}".format(self.level))

    def do_neo4jconfig(self, args):
        global neo4j
        neo4j = safe_import_neo4j()
        if neo4j is None:
            return

        print("Current Settings")
        print("DB Url: {}".format(self.url))
        print("DB Username: {}".format(self.username))
        print("DB Password: {}".format(self.password))
        print("Use encryption: {}".format(self.use_encryption))
        print("")

        self.url = self.m.input_default("Enter DB URL", self.url)
        self.username = self.m.input_default(
            "Enter DB Username", self.username)
        self.password = self.m.input_default_password(
            "Enter DB Password", self.password)
        self.use_encryption = self.m.input_yesno(
            "Use encryption?", self.use_encryption)

        print("")
        print("Confirmed Settings:")
        print("DB Url: {}".format(self.url))
        print("DB Username: {}".format(self.username))
        print("DB Password: {}".format(self.password))
        print("Use encryption: {}".format(self.use_encryption))
        print("")
        print("Testing DB Connection")
        self.test_db_conn()

    def do_setdomain(self, args):
        passed = args
        if passed != "":
            try:
                self.domain = passed.upper()
                return
            except ValueError:
                pass

        self.domain = self.m.input_default("Domain", self.domain).upper()
        print("")
        print("New Settings:")
        print("Domain: {}".format(self.domain))

    def do_exit(self, args):
        raise KeyboardInterrupt

    def do_connect(self, args):
        self.test_db_conn()

    def remove_constraints(self, session):
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

    def do_cleardb(self, args):
        if not self.connected:
            print("Not connected to database. Use connect first")
            return

        print("Clearing Database")
        d = self.driver
        session = d.session()

        # Delete nodes and edges with batching into 10k objects - From DBCreator
        total = 1
        while total > 0:
            result = session.run(
                "MATCH (n) WITH n LIMIT 10000 DETACH DELETE n RETURN count(n)")
            for r in result:
                total = int(r['count(n)'])

        self.remove_constraints(session)

        session.close()

        print("DB Cleared and Schema Set")

    def do_setparams(self, args):
        passed = args
        if passed != "":
            try:
                json_path = passed
                self.parameters = get_parameters_from_json(json_path)
                self.parameters_json_path = json_path
                print_all_parameters(self.parameters)
                return
            except ValueError:
                pass

        json_path = self.m.input_default(
            "Parameters JSON file (copy and paste the full path of your parameter JSON file)",
            self.parameters_json_path)
        self.parameters = get_parameters_from_json(json_path)
        if self.parameters == DEFAULT_CONFIGURATIONS:
            self.parameters_json_path = "DEFAULT"
        else:
            self.parameters_json_path = json_path

        print_all_parameters(self.parameters)

    def test_db_conn(self):
        if neo4j is None:
            print("Please setup Neo4J database first using 'neo4jconfig'")
            return

        try:
            if self.driver is not None:
                self.driver.close()
            self.driver = neo4j.GraphDatabase.driver(
                self.url, auth=(self.username, self.password), encrypted=self.use_encryption)
            with self.driver.session() as session:
                result = session.run("RETURN 1")
            self.connected = True
            print("Database Connection Successful!")
        except neo4j.exceptions.AuthError:
            print("Authentication failed: Incorrect username or password.")
        except neo4j.exceptions.ServiceUnavailable:
            print(
                "Neo4J Service unavailable: Unable to connect to the database. Please make sure you have activated Neo4J.")
        except:
            self.connected = False
            print("Database Connection Failed. Check your settings.")

    def do_importdb(self, args):
        if not self.connected:
            print("Neo4J connection has not been configured yet. Please proceed 'neo4jconfig' first.")
            return
        print(
            "Please input the name of a JSON file in the folder 'generated_datasets' (excluding the file extension). Otherwise, provide the full path to your intended JSON file")
        print("If you want to import the dataset you have just generated in this terminal, please click Enter")
        dataset_name = input("Dataset to be imported: ")
        if not dataset_name:
            if self.dbname is None:
                print("No dataset generated recently")
                return
            path = f"{os.getcwd()}/generated_datasets/{self.dbname}.json"
        else:
            path = f"{os.getcwd()}/generated_datasets/{dataset_name}.json"
            if not os.path.exists(path):
                path = dataset_name
                if not os.path.exists(path):
                    print("There is no such file.")
                    return
        try:
            self.test_db_conn()
        except:
            return

        session = self.driver.session()

        try:
            self.do_cleardb("a")
            query = f"PROFILE CALL apoc.periodic.iterate(\"CALL apoc.import.json('{path}')\", \"RETURN 1\", {{batchSize:1000}})"
            print("========== IMPORT PROCESS ==========")
            session.run(query)
            print("Import has finished")
        except neo4j.exceptions.Neo4jError as e:
            print(f"Neo4jError occurred: {e}")
        except Exception as e:
            print(f"An error occurred: {e}")

        session.close()

    def do_generate(self, args):

        print(self.level)
        passed = args
        if passed != "":
            try:
                self.json_file_name = passed
            except ValueError:
                self.json_file_name = None

        # Disable Neo4J from ADSynth
        # self.test_db_conn()
        # self.do_cleardb("a")

        reset_DB()

        self.generate_data()
        self.old_domain = self.domain

    def generate_data(self):
        start_ = timer()
        seed_number = get_single_int_param_value("seed", self.parameters)
        if seed_number > 0:
            random.seed(seed_number)

        # if not self.connected:
        #     print("Not connected to database. Use connect first")
        #     return

        domain_dn = get_domain_dn(self.domain)

        nTiers = get_num_tiers(self.parameters)

        # RIDs below 1000 are used for default principals.
        # RIDs of other objects should start from 1000.
        # Idea Ref: DBCreator and https://www.itprotoday.com/security/q-what-are-exact-roles-windows-accounts-sid-and-more-specifically-its-rid-windows-security
        ridcount.extend([1000])

        computers = []

        users = []

        convert_to_digraph = get_single_int_param_value("convert_to_directed_graphs", self.parameters)

        # session = self.driver.session()

        print(f"Initiating the Active Directory Domain - {self.domain}")
        functional_level = create_domain(self.domain, self.base_sid, domain_dn,
                                         self.parameters)  # Ref: ADSimulator, DBCreator

        print("Building the fundamental framework of a tiered Active Directory model")
        create_ad_skeleton(self.domain, self.base_sid, self.parameters, nTiers)

        # -------------------------------------------------------------
        # Active Directory Default OUs, Groups and GPOs
        # Ref: DBCreator and ADSimulator have produced some default AD objects and relationships in their code
        # Utilising Microsoft documentation as a knowledge base, I migrated their codes into ADSynth built-in database.

        print("Creating the default domain groups")
        create_default_groups(self.domain, self.base_sid,
                              self.old_domain)  # Ref: ADSimulator, DBCreator and Microsoft, https://learn.microsoft.com/en-us/windows-server/identity/ad-ds/manage/understand-security-groups

        print("Creating the admin groups")
        create_admin_groups(self.domain, self.base_sid, nTiers)

        ddp = cs(str(uuid.uuid4()), self.base_sid).upper()
        ddcp = cs(str(uuid.uuid4()), self.base_sid).upper()
        dcou = cs(str(uuid.uuid4()), self.base_sid).upper()
        gpos_container = cs(str(uuid.uuid4()), self.base_sid).upper()

        print("Creating GPOs container")
        create_gpos_container(self.domain, domain_dn, gpos_container)

        print("Creating default GPOs")
        create_default_gpos(self.domain, domain_dn, ddp,
                            ddcp)  # Ref: DBCreator, ADSimulator and Microsoft, https://learn.microsoft.com/en-us/openspecs/windows_protocols/ms-gpod/566e983e-3b72-4b2d-9063-a00ebc9514fd

        print("Creating Domain Controllers OU")
        create_domain_controllers_ou(self.domain, domain_dn,
                                     dcou)  # Ref: DBCreator, ADSimulator and Microsoft, https://learn.microsoft.com/en-us/windows-server/identity/ad-ds/plan/delegating-administration-of-default-containers-and-ous

        print("Applying Default GPOs")
        apply_default_gpos(self.domain, ddp, ddcp, dcou)  # Ref: DBCreator, ADSimulator

        # ENTERPRISE ADMINS
        # Adding Ent Admins -> High Value Targets
        print("Creating Enterprise Admins ACLs")
        create_enterprise_admins_acls(
            self.domain)  # Ref: DBCreator, ADSimulator and Microsoft, https://learn.microsoft.com/en-us/windows-server/identity/ad-ds/manage/understand-security-groups

        # ADMINISTRATORS
        # Adding Administrators -> High Value Targets
        print("Creating Administrators ACLs")
        create_administrators_acls(
            self.domain)  # Ref: DBCreator, ADSimulator and Microsoft, https://learn.microsoft.com/en-us/windows-server/identity/ad-ds/manage/understand-security-groups

        # DOMAIN ADMINS
        # Adding Domain Admins -> High Value Targets
        print("Creating Domain Admins ACLs")
        create_domain_admins_acls(
            self.domain)  # Ref: DBCreator, ADSimulator and Microsoft, https://learn.microsoft.com/en-us/windows-server/identity/ad-ds/manage/understand-security-groups

        # DC Groups
        # Extra ENTERPRISE READ-ONLY DOMAIN CONTROLLERS
        print("Generating DC groups ACLs")
        create_default_dc_groups_acls(
            self.domain)  # Ref: DBCreator, ADSimulator and Microsoft, https://learn.microsoft.com/en-us/windows-server/identity/ad-ds/manage/understand-security-groups

        # DOMAIN CONTROLLERS
        # Ref: ADSimulator, DBCreator and Microsoft, https://learn.microsoft.com/en-us/openspecs/windows_protocols/ms-authsod/c4012a57-16a9-42eb-8f64-aa9e04698dca
        print("Creating Domain Controllers")
        dc_properties_list, domain_controllers = generate_dcs(self.domain, self.base_sid, domain_dn, dcou,
                                                              self.current_time, self.parameters,
                                                              functional_level)  # O(1)

        # -------------------------------------------------------------
        # GPOs - Creating GPOs for the root OUs in a Tier Model
        print("Applying GPOs to critical OUs and tiers")
        apply_gpos(self.domain, self.base_sid,
                   nTiers)  # Ref: Russell Smith, https://petri.com/keep-active-directory-secure-using-privileged-access-workstations/, https://volkandemirci.org/2022/01/17/privileged-access-workstations-kurulumu-ve-yapilandirilmasi-2/

        # Impose restriction on non-privileged OU
        apply_restriction_gpos(self.domain, self.base_sid, self.parameters)

        # Place all GPOs in the GPOs container
        place_gpos_in_container(self.domain, gpos_container)

        # -------------------------------------------------------------
        # DEFAULT USERS and group relationships
        # Ref: ADSimulator produced these in their code
        # Utilising Microsoft documentation as a knowledge base, I migrated their code into ADSynth built-in database.
        # https://learn.microsoft.com/en-us/windows-server/identity/ad-ds/manage/understand-default-user-accounts
        print("Generating default users")
        generate_guest_user(self.domain, self.base_sid, self.parameters)
        generate_default_account(self.domain, self.base_sid, self.parameters)
        generate_administrator(self.domain, self.base_sid, self.parameters)
        generate_krbtgt_user(self.domain, self.base_sid, self.parameters)
        link_default_users_to_domain(self.domain, self.base_sid)

        # Ref: ADSimulator and Microsoft, https://learn.microsoft.com/en-us/windows-server/identity/ad-ds/manage/understand-default-user-accounts
        print("Creating ACLs for default users")
        create_default_users_acls(self.domain, self.base_sid)

        # Ref: ADSimulator and Microsoft, https://learn.microsoft.com/en-us/windows-server/identity/ad-ds/manage/understand-security-groups
        # Adminstrator account is Member of High value groups
        print("Creating memberships for Administrator group")
        create_adminstrator_memberships(self.domain)

        # Ref: ADSimulator and Microsoft, https://learn.microsoft.com/en-us/windows-server/identity/ad-ds/manage/understand-security-groups
        print("Assigning members to default groups")
        generate_default_member_of(self.domain, self.base_sid, self.old_domain)

        # Ref: ADSimulator and Microsoft, https://learn.microsoft.com/en-us/windows-server/identity/ad-ds/plan/security-best-practices/appendix-b--privileged-accounts-and-groups-in-active-directory
        print("Creating ACLs for default groups")
        create_default_groups_acls(self.domain, self.base_sid)

        # -------------------------------------------------------------
        # Creating users
        num_users = get_int_param_value("User", "nUsers", self.parameters)
        print(f"Creating {num_users} users")

        # Get a list of enabled and disabled users
        users, disabled_users = generate_users(self.domain, self.base_sid, num_users, self.current_time,
                                               self.first_names, self.last_names,
                                               self.parameters)  # Ref: ADSimulator, DBCreator

        # Segragate admin and regular users
        perc_admin = get_perc_param_value("Admin", "Admin_Percentage", self.parameters)
        all_admins, all_enabled_users = segregate_list(users, [perc_admin, 100 - perc_admin])

        # Segregate admins and misconfigured admins in regular Users OU

        misconfig_admin_regular_perc = get_perc_param_value("nodeMisconfig", "admin_regular", self.parameters)
        if misconfig_admin_regular_perc > 50:
            misconfig_admin_regular_perc = DEFAULT_CONFIGURATIONS["nodeMisconfig"]["admin_regular"]
        admin, misconfig_admin = segregate_list(all_admins,
                                                [100 - misconfig_admin_regular_perc, misconfig_admin_regular_perc])

        # Segregate regular users, misconfigured users in Admin OU and in Computers OU
        misconfig_user_comp_perc = get_perc_param_value("nodeMisconfig", "user_comp", self.parameters)
        if misconfig_admin_regular_perc + misconfig_user_comp_perc > 50:
            misconfig_admin_regular_perc = DEFAULT_CONFIGURATIONS["nodeMisconfig"]["admin_regular"]
            misconfig_user_comp_perc = DEFAULT_CONFIGURATIONS["nodeMisconfig"]["user_comp"]
        enabled_users, misconfig_regular_users, misconfig_users_comps = \
            segregate_list(all_enabled_users,
                           [100 - misconfig_admin_regular_perc - misconfig_user_comp_perc, misconfig_admin_regular_perc,
                            misconfig_user_comp_perc])

        # -------------------------------------------------------------
        # Creating COMPUTERS
        num_computers = get_int_param_value("Computer", "nComputers", self.parameters)
        print("Generating", str(num_computers), "computers")

        # Ref: ADSimulator, DBCreator, BadBlood
        #      Microsoft, https://learn.microsoft.com/en-us/security/privileged-access-workstations/privileged-access-devices
        computers, PAW, Servers, Workstations = generate_computers(self.domain, self.base_sid, num_computers, computers,
                                                                   self.current_time, self.parameters)

        Workstations, misconfig_workstations = segregate_list(Workstations, [100 - misconfig_user_comp_perc,
                                                                             misconfig_user_comp_perc])
        place_computers_in_tiers(self.domain, self.base_sid, nTiers, self.parameters, PAW, Servers, Workstations,
                                 misconfig_users_comps)

        # -------------------------------------------------------------
        # Admin Users
        print("Allocate Admin Users to tiers")

        # Retrieve members of server operators and print operators
        # to later generate sessions on Domain Controllers
        server_operators = []  # Server Operators
        print_operators = []  # Print Operators

        place_admin_users_in_tiers(self.domain, self.base_sid, nTiers, admin, misconfig_regular_users, server_operators,
                                   print_operators, self.parameters)

        # Non-admin Users
        print("Allocate non-admin users to tiers")
        place_normal_users_in_tiers(self.domain, enabled_users, disabled_users, misconfig_admin, misconfig_workstations,
                                    nTiers)

        # -------------------------------------------------------------
        # Creating GROUPS
        print("Creating distribution groups and security groups")
        num_regular_groups = create_groups(self.domain, self.base_sid, self.parameters, nTiers)

        print("Nesting groups")
        nest_groups(self.domain, self.parameters)  # Ref: DBCreator and ADSimulator

        # Adding Users to Groups
        # Admin users have been place into admistrative tiers. Now comes the normal users
        print("Adding users to groups")
        it_users = place_users_in_groups(self.domain, nTiers, self.parameters)

        # -------------------------------------------------------------
        print("Generate sessions")
        create_sessions(nTiers, PAW_TIERS, S_TIERS, WS_TIERS, self.parameters)

        if self.misconfig_enabled:
            print("Generate cross-tier sessions")
            create_misconfig_sessions(nTiers, self.level, self.parameters, len(enabled_users) + len(admin))

        # Print Operators and Server Operators can log into Domain Controllers
        # Idea Ref: Microsoft, https://learn.microsoft.com/en-us/windows-server/identity/ad-ds/manage/understand-security-groups
        print("Print Operators and Server Operators can log into Domain Controllers")
        create_dc_sessions(domain_controllers, server_operators, print_operators)  # O(num of Domain Controllers)

        # -------------------------------------------------------------
        # Generate non-ACL Permissions
        print("Generating non-ACL permissions")
        create_control_management_permissions(self.domain, nTiers, False, self.parameters, convert_to_digraph)

        if self.misconfig_enabled:
            print("Generating misconfigured non-ACL permissions on individuals")
            create_misconfig_permissions_on_individuals(nTiers, ADMIN_USERS, ENABLED_USERS, self.level, self.parameters,
                                                        len(enabled_users) + len(admin))

            print("Generating misconfigured permissions on sets - From groups to OUs")
            num_local_admin_groups = sum(len(subarray) for subarray in LOCAL_ADMINS)
            create_misconfig_permissions_on_groups(self.domain, nTiers, self.level, self.parameters,
                                                   num_local_admin_groups)

            print("Generating misconfigured membership - Group Nesting")
            create_misconfig_group_nesting(self.domain, nTiers, self.level, self.parameters, num_regular_groups)

        # -------------------------------------------------------------
        #  Generate ACL Permissions, including genericall, genericwrite, writeowner, ....
        print("Creating ACLs permissions")
        create_control_management_permissions(self.domain, nTiers, True, self.parameters, convert_to_digraph)

        # -------------------------------------------------------------
        print("Adding Admin rights")
        assign_administration_to_admin_principals(self.domain, nTiers, convert_to_digraph)

        print("Adding Local Admin rights")
        assign_local_admin_rights(self.domain, nTiers, self.parameters, convert_to_digraph)

        # -------------------------------------------------------------
        # Default ACLs
        # Ref: ADSimulator
        create_default_AllExtendedRights(self.domain, nTiers, convert_to_digraph)  # Ref: ADSimulator
        create_default_GenericWrite(self.domain, nTiers, self.parameters, convert_to_digraph)  # Ref: ADSimulator
        create_default_owns(self.domain, convert_to_digraph)  # Ref: ADSimulator
        create_default_write_dacl_owner(self.domain, nTiers, self.parameters, convert_to_digraph)  # Ref: ADSimulator
        create_default_GenericAll(self.domain, nTiers, self.parameters, convert_to_digraph)  # Ref: ADSimulator

        # -------------------------------------------------------------
        # Kerberoastable users
        print("Creating Kerberoastable users")
        create_kerberoastable_users(nTiers, self.parameters)  # O(nUsers * perc of Kerberoastable)

        num_nodes = len(NODES)
        num_edges = len(dict_edges)
        print("Num of nodes = ", len(NODES))
        print("Num of edges = ", len(dict_edges))

        try:
            print("Graph density = ", round(num_edges / (num_nodes * (num_nodes - 1)), 5))
        except:
            pass

        for i in NODE_GROUPS:
            print("Number of ", i, " = ", len(NODE_GROUPS[i]))

        perc_misconfig_sessions = get_perc_param_value("perc_misconfig_sessions", "Low", self.parameters) / 100
        if self.misconfig_enabled:
            num_misconfig = int(perc_misconfig_sessions * (len(enabled_users) + len(admin)))
            print(
                f"Number of regular users = {len(enabled_users) + len(admin)} --- Num misconfig sessions = {num_misconfig}")
            perc_misconfig_permissions = get_perc_param_value("perc_misconfig_permissions", "Low",
                                                              self.parameters) / 100
            num_misconfig = int(perc_misconfig_permissions * (len(enabled_users) + len(admin)))
            print(
                f"Number of regular users = {len(enabled_users) + len(admin)} --- Num misconfig permissions = {num_misconfig}")
        else:

            print(
                f"Number of regular users = {len(enabled_users) + len(admin)}")

            print(
                f"Number of regular users = {len(enabled_users) + len(admin)}  ")

        current_datetime = datetime.now()
        # Format the date and time to include seconds
        filename = current_datetime.strftime("%Y-%m-%d_%H-%M-%S-%f")[:-3]
        if self.misconfig_enabled:
            print("Dump to JSON file")

            with open(
                    f"/Users/yagzanmanjunaath/UniWorkspace/ResearchMethods/Part2/ADSynth/generated_datasets/{filename}.json",
                    "w") as f:
                for obj in NODES:
                    obj["type"] = "node"
                    # Use json.dumps() to convert the object to a JSON string without square brackets
                    json_str = json.dumps(obj, separators=(',', ':'))
                    # Write the JSON string to the file with a newline character
                    f.write(json_str + '\n')

            # Open the file in append mode
            with open(
                    f"/Users/yagzanmanjunaath/UniWorkspace/ResearchMethods/Part2/ADSynth/generated_datasets/{filename}.json",
                    'a') as f:
                print(f"generated_datasets/{filename}.json")
                for obj in EDGES:
                    # Use json.dumps() to convert the object to a JSON string without square brackets
                    json_str = json.dumps(obj, separators=(',', ':'))
                    # Write the JSON string to the file with a newline character
                    f.write(json_str + '\n')

            self.dbname = filename
        # ===============================================

        end_ = timer()
        print("Execution time = ", end_ - start_)

        update_graph_db_with_temp_file(self.driver.session(), "create")
        path = f"{os.getcwd()}/generated_datasets/{filename}.json"
        query = f"PROFILE CALL apoc.periodic.iterate(\"CALL apoc.import.json('{path}')\", \"RETURN 1\", {{batchSize:1000}})"
        # session.run(query)
        # session.close()

        print("Database Generation Finished!")

    def write_json(self, session):
        json_path = os.getcwd() + "/" + self.json_file_name
        query = "CALL apoc.export.json.all('" + json_path + "',{useTypes:true})"
        session.run(query)
        print("Graph exported in", json_path)

    def do_initialise_AD_graph_from_json(self, args):
        global neo4j
        neo4j = safe_import_neo4j()
        if neo4j is None:
            return

        self.password = "admin1234"
        print("Current Settings")
        print("DB Url: {}".format(self.url))
        print("DB Username: {}".format(self.username))
        print("DB Password: {}".format(self.password))
        print("Use encryption: {}".format(self.use_encryption))
        continue_with_configured_db = True
        # self.m.input_yesno(
        #     "Do you wish to continue with this Db config?",False))
        if not continue_with_configured_db:
            print("Configure using `neo4j_config`")
            return
        self.test_db_conn()

        parts = args.split(maxsplit=1)

        arg_json_path = parts[0] if len(parts) > 0 else ""
        level = parts[1] if len(parts) > 1 else "High"

        print("JSON Path:", arg_json_path)
        print("Level:", level)

        is_params_set = False
        print(f"Configuration level ${level}")

        if arg_json_path:
            try:
                json_path = arg_json_path
                self.parameters = get_parameters_from_json(json_path)
                self.parameters_json_path = json_path
                args = json_path
                print_all_parameters(self.parameters)
                is_params_set = True
                print(f"Is param set ${is_params_set}")
                # is_misconfig_enabled = self.m.input_default(
                #     "Enable initial misconfiguration - (Y/N)",
                #     "Y")
                # if is_misconfig_enabled == "Y":
                #     self.misconfig_enabled = True
                # else:
                #     self.misconfig_enabled = False

            except ValueError as v:
                print(v)
                pass

        if not is_params_set:
            json_path = self.m.input_default(
                "Parameters JSON file (copy and paste the full path of your parameter JSON file)",
                self.parameters_json_path)
            self.parameters = get_parameters_from_json(json_path)
            args = json_path
            print_all_parameters(self.parameters)

        self.do_generate(args)
        populate_node_tiers()

    def do_isolated_injection(self, args):
        injection_type = input("Injection Type [session/i_perm/g_perm/nesting]  : ")
        args = "isolated"

        if injection_type == "session":
            self.session_injection(args)
        elif injection_type == "i_perm":
            self.indi_permission_injection(args)

    def run_injection_schedule(self, schedule_type, run_sequence=None):
        if run_sequence is None:
            run_sequence = []
        if schedule_type == "isolated":
            if run_sequence and len(run_sequence) == 1 and run_sequence[0] in ["session", "i_perm", "g_perm",
                                                                               "nesting"]:
                self.run_single_injection(run_sequence[0], schedule_type)

        elif schedule_type == "mixed":
            for injection_type in ["session", "i_perm", "g_perm", "nesting"]:
                self.run_single_injection(injection_type, schedule_type)

        elif schedule_type == "sequence" and run_sequence and len(run_sequence) > 0:
            for injection_type in run_sequence:
                self.run_single_injection(injection_type, schedule_type)

    def run_single_injection(self, injection_type, mode):
        if injection_type == "session":
            self.session_injection(mode)
        elif injection_type == "i_perm":
            self.indi_permission_injection(mode)
        elif injection_type == "g_perm":
            self.grp_permission_injection(mode)
        elif injection_type == "nesting":
            self.grp_nesting_injection(mode)



    def session_injection(self, args):
        if len(NODES) == 0:
            print("====================================================================")
            print("== No graph intialised to generate misconfigurations ==")
            return
        nTiers = get_num_tiers(self.parameters)
        num_users = get_int_param_value("User", "nUsers", self.parameters)
        num_computers = get_int_param_value("Computer", "nComputers", self.parameters)

        logging.info("====================================================================")
        logging.info("== Injecting Session Misconfigurations ==")
        logging.info("Num of Users %s", num_users)
        logging.info("Num of Computers %s", num_computers)

        N_baseline_session = get_baseline_from_AD("session",None)

        # Assuming Max of 10% of misconfigurations for fine grained analysis
        max_perc_misconfig_sessions = 0.1
        num_misconfig = int(max_perc_misconfig_sessions * num_users)
        high_value_target_name = "DOMAIN ADMINS@TESTLAB.LOCALE"

        misconfig_metrics_per_itr = {}

        base_filename = os.path.splitext(os.path.basename(self.parameters_json_path))[0]

        for itr in range(self.R):
            init_experiment_state()
            networkx_graph = create_networkx_graph()

            misconfig_growth_metrics = {}
            for misconfig_session_count in range(1, num_misconfig + 1):
                print(f"Injecting {misconfig_session_count}")
                logging.info(f"New Session {misconfig_session_count}")
                p = misconfig_session_count / N_baseline_session
                networkx_graph = create_misconfig_sessions_from_entrypoints_multi_tiers(nTiers, networkx_graph,
                                                                                        self.driver.session(),
                                                                                        misconfig_session_count,
                                                                                        self.level, self.parameters)
                # if misconfig_session_count % 600 == 0:
                networkx_graph = create_networkx_graph()
                find_user_count_with_path_to_DA(networkx_graph, high_value_target_name, misconfig_session_count,
                                                misconfig_growth_metrics)

                misconfig_growth_metrics[misconfig_session_count]["p"] = p
                misconfig_growth_metrics[misconfig_session_count]["X"] = exposure_X(
                    misconfig_growth_metrics[misconfig_session_count]["reachable_users_count"],
                    misconfig_growth_metrics[misconfig_session_count]["reachable_comps_count"], num_users,
                    num_computers)
                indicators_hci_csm_tbs(EXP_EDGES, misconfig_growth_metrics, misconfig_session_count, {2}, 1.0)
                pbcc_result = pbcc_bounded_bfs_footholds(networkx_graph, WS_TIERS[2], high_value_target_name)
                misconfig_growth_metrics[misconfig_session_count]["pbcc"] = pbcc_result["pbcc"]

                misconfig_growth_metrics = compute_delta_X(misconfig_growth_metrics)
                p_star = find_p_star(misconfig_growth_metrics)

                # corr = np.corrcoef(HCI, deltaX)[0,1]

                logging.info(
                    "step=%d users=%d comps=%d p=%.6f X=%.4f delta_X=%.6f p_star=%.6f HCI=%.4f CSM=%.4f TBS=%.4f PBCC=%.4f",
                    misconfig_session_count,
                    misconfig_growth_metrics[misconfig_session_count]["reachable_users_count"],
                    misconfig_growth_metrics[misconfig_session_count]["reachable_comps_count"],
                    misconfig_growth_metrics[misconfig_session_count]["p"],
                    misconfig_growth_metrics[misconfig_session_count]["X"],
                    misconfig_growth_metrics[misconfig_session_count].get("delta_X", 0.0),
                    p_star,
                    misconfig_growth_metrics[misconfig_session_count]["HCI"],
                    misconfig_growth_metrics[misconfig_session_count]["CSM"],
                    misconfig_growth_metrics[misconfig_session_count]["TBS"],
                    misconfig_growth_metrics[misconfig_session_count]["pbcc"]
                )
            number_of_misconfigs = sorted(misconfig_growth_metrics.keys())

            corr = compute_hub_correlation(misconfig_growth_metrics)
            logging.info("corr(HCI, ΔX) = %.4f", corr)

            HCI = []
            deltaX = []

            for m in misconfig_growth_metrics.values():
                if "delta_X" in m:
                    HCI.append(m["HCI"])
                    deltaX.append(m["delta_X"])

            if itr == self.R - 1 and not self.skip_plots:
                plot_plot_chart(
                    x_values=HCI,
                    y_values=deltaX,
                    x_label="HCI",
                    y_label="ΔX",
                    title="Hub Concurrency vs Exposure Jump",
                    additional_info={"itr":itr},
                    plot_type="scatter"
                )

            misconfig_metrics_per_itr[itr] = misconfig_growth_metrics
            save_experiment_state(itr)
            saveTofile(self, f"session-{itr}-{base_filename}.json")
            # clear_exp_neo4j_db(self.driver.session())
            # update_graph_db_with_temp_file(self.driver.session(), f"misconfig-session-temp={itr}")
            # tabulate_experiment_results(self.driver.session(),misconfig_growth_metrics)
            # if itr == 0 and not self.skip_plots:
            if itr == self.R-1 :
                plot_metrics(num_users, num_computers, num_misconfig, base_filename, misconfig_growth_metrics)

        mu = compute_mu(misconfig_metrics_per_itr, "X")
        logging.info("Mu :%s", mu)

        sigma2 = compute_sigma2(misconfig_metrics_per_itr, "X")
        logging.info("Sigma2 :%s", sigma2)

        if not sigma2:
            logging.warning("Sigma2 is empty. Cannot compute p_star.")
            p_star = None
        else:
            p_star = max(sigma2, key=sigma2.get)
        logging.info("P* :%s", p_star)

        run_metrics = misconfig_metrics_per_itr[0]


        steps = sorted(run_metrics.keys())

        X_values = [run_metrics[s]["X"] for s in steps]

        ci = compute_mu_sigma_ci(X_values, 0.95)
        logging.info("CI :%s", ci)

        logging.info("====================================================================")

        if not self.skip_plots :
                plot_plot_chart(
                    x_values=list(mu.keys()),
                    y_values=list(mu.values()),
                    x_label="p",
                    y_label="μ(p)",
                    title="Mean Exposure vs Misconfiguration Level",
                    additional_info={"R": self.R},
                    plot_type="line"
                )

                plot_plot_chart(
                    x_values=list(sigma2.keys()),
                    y_values=list(sigma2.values()),
                    x_label="p",
                    y_label="σ²(p)",
                    title="Exposure Variance vs Misconfiguration Level",
                    additional_info={"R": self.R},
                    plot_type="line"
                )

        save_all_experiment_states_to_json(
            f"/Users/yagzanmanjunaath/UniWorkspace/ResearchMethods/Part2/ADSynth/generated_datasets/experiment_session_{base_filename}.json",
        )

        with open(
                f"/Users/yagzanmanjunaath/UniWorkspace/ResearchMethods/Part2/ADSynth/generated_datasets/mgm_session_{base_filename}.json",
                "w") as f:
            json.dump(misconfig_metrics_per_itr, f, indent=4)

        calc_thresholds_and_jump_labels(misconfig_metrics_per_itr[0])

    def indi_permission_injection(self, args):
        if len(NODES) == 0:
            print("====================================================================")
            print("== No graph intialised to generate misconfigurations ==")
            return
        nTiers = get_num_tiers(self.parameters)

        num_users = get_int_param_value("User", "nUsers", self.parameters)

        num_computers = get_int_param_value("Computer", "nComputers", self.parameters)

        CP = ["AdminTo", "CanRDP", "CanPSRemote", "ExecuteDCOM", "AllowedToDelegate", "ReadLAPSPassword", "SQLAdmin",
              "AllowedToAct"]

        logging.info("====================================================================")
        logging.info("== Injecting Individual Permission Misconfigurations ==")
        logging.info("Num of Users %s", num_users)
        logging.info("Num of Computers %s", num_computers)

        N_baseline_indi_permission = get_baseline_from_AD("i_perm", CP)

        misconfig_perc = get_perc_param_value("perc_misconfig_permissions", self.level, self.parameters) / 100
        # num_misconfig = int(misconfig_perc * num_users)
        # num_misconfig = 10
        num_misconfig = int(misconfig_perc * num_users)
        misconfig_to_tier_0_allow, misconfig_to_tier_0_limit = get_misconfig_dict_param_value(
            "misconfig_permissions_to_tier_0", self.parameters)

        misconfig_metrics_per_itr = {}
        base_filename = os.path.splitext(os.path.basename(self.parameters_json_path))[0]

        high_value_target_name = "DOMAIN ADMINS@TESTLAB.LOCALE"

        misconfig_metrics_per_itr = {}

        base_filename = os.path.splitext(os.path.basename(self.parameters_json_path))[0]

        for itr in range(self.R):
            if args == "isolated":
                init_experiment_state()
            else:
                restore_experiment_state(itr)

            networkx_graph = create_networkx_graph()

            misconfig_growth_metrics = {}
            for misconfig_indi_permission_count in range(1, num_misconfig + 1):
                print(f"Injecting {misconfig_indi_permission_count}")
                logging.info(f"New Indi Permission {misconfig_indi_permission_count}")
                p = misconfig_indi_permission_count / N_baseline_indi_permission
                networkx_graph = create_misconfig_permissions_on_individuals_from_entrypoints(
                    nTiers,
                    EXP_ADMIN_USERS,
                    EXP_ENABLED_USERS,
                    self.level,
                    self.parameters,
                    num_users,
                    CP,
                    misconfig_to_tier_0_allow,
                    misconfig_to_tier_0_limit,
                    itr,
                    networkx_graph
                )
                # if misconfig_session_count % 600 == 0:
                networkx_graph = create_networkx_graph()
                find_user_count_with_path_to_DA(networkx_graph, high_value_target_name, misconfig_indi_permission_count,
                                                misconfig_growth_metrics)

                misconfig_growth_metrics[misconfig_indi_permission_count]["p"] = p
                misconfig_growth_metrics[misconfig_indi_permission_count]["X"] = exposure_X(
                    misconfig_growth_metrics[misconfig_indi_permission_count]["reachable_users_count"],
                    misconfig_growth_metrics[misconfig_indi_permission_count]["reachable_comps_count"], num_users,
                    num_computers)
                indicators_hci_csm_tbs(EXP_EDGES, misconfig_growth_metrics, misconfig_indi_permission_count, {2}, 1.0)
                pbcc_result = pbcc_bounded_bfs_footholds(networkx_graph, WS_TIERS[2], high_value_target_name)
                misconfig_growth_metrics[misconfig_indi_permission_count]["pbcc"] = pbcc_result["pbcc"]

                misconfig_growth_metrics = compute_delta_X(misconfig_growth_metrics)
                p_star = find_p_star(misconfig_growth_metrics)

                # corr = np.corrcoef(HCI, deltaX)[0,1]

                logging.info(
                    "step=%d users=%d comps=%d p=%.6f X=%.4f delta_X=%.6f p_star=%.6f HCI=%.4f CSM=%.4f TBS=%.4f PBCC=%.4f",
                    misconfig_indi_permission_count,
                    misconfig_growth_metrics[misconfig_indi_permission_count]["reachable_users_count"],
                    misconfig_growth_metrics[misconfig_indi_permission_count]["reachable_comps_count"],
                    misconfig_growth_metrics[misconfig_indi_permission_count]["p"],
                    misconfig_growth_metrics[misconfig_indi_permission_count]["X"],
                    misconfig_growth_metrics[misconfig_indi_permission_count].get("delta_X", 0.0),
                    p_star,
                    misconfig_growth_metrics[misconfig_indi_permission_count]["HCI"],
                    misconfig_growth_metrics[misconfig_indi_permission_count]["CSM"],
                    misconfig_growth_metrics[misconfig_indi_permission_count]["TBS"],
                    misconfig_growth_metrics[misconfig_indi_permission_count]["pbcc"]
                )
            number_of_misconfigs = sorted(misconfig_growth_metrics.keys())

            corr = compute_hub_correlation(misconfig_growth_metrics)
            logging.info("corr(HCI, ΔX) = %.4f", corr)

            HCI = []
            deltaX = []

            for m in misconfig_growth_metrics.values():
                if "delta_X" in m:
                    HCI.append(m["HCI"])
                    deltaX.append(m["delta_X"])

            if itr == self.R - 1 and not self.skip_plots:
                plot_plot_chart(
                    x_values=HCI,
                    y_values=deltaX,
                    x_label="HCI",
                    y_label="ΔX",
                    title="Hub Concurrency vs Exposure Jump (i_perm)",
                    additional_info={},
                    plot_type="scatter"
                )

            misconfig_metrics_per_itr[itr] = misconfig_growth_metrics
            save_experiment_state(itr)
            saveTofile(self, f"i_perm-{itr}-{base_filename}.json")
            # clear_exp_neo4j_db(self.driver.session())
            # update_graph_db_with_temp_file(self.driver.session(), f"misconfig-session-temp={itr}")
            # tabulate_experiment_results(self.driver.session(),misconfig_growth_metrics)
            if itr == 0:
                plot_metrics(num_users, num_computers, num_misconfig, base_filename, misconfig_growth_metrics)

        mu = compute_mu(misconfig_metrics_per_itr, "HCI")
        logging.info("Mu :%s", mu)

        sigma2 = compute_sigma2(misconfig_metrics_per_itr, "HCI")
        logging.info("Sigma2 :%s", sigma2)

        if not sigma2:
            logging.warning("Sigma2 is empty. Cannot compute p_star.")
            p_star = None
        else:
            p_star = max(sigma2, key=sigma2.get)
        logging.info("P* :%s", p_star)
        run_metrics = misconfig_metrics_per_itr[0]

        steps = sorted(run_metrics.keys())

        X_values = [run_metrics[s]["X"] for s in steps]

        ci = compute_mu_sigma_ci(X_values, 0.95)
        logging.info("CI :%s", ci)

        logging.info("====================================================================")
        if not self.skip_plots :
                plot_plot_chart(
                    x_values=list(mu.keys()),
                    y_values=list(mu.values()),
                    x_label="p",
                    y_label="μ(p)",
                    title="Mean Exposure vs Misconfiguration Level  (i_perm)",
                    additional_info={"R": self.R},
                    plot_type="line"
                )

                plot_plot_chart(
                    x_values=list(sigma2.keys()),
                    y_values=list(sigma2.values()),
                    x_label="p",
                    y_label="σ²(p)",
                    title="Exposure Variance vs Misconfiguration Level (i_perm)",
                    additional_info={"R": self.R},
                    plot_type="line"
                )

        save_all_experiment_states_to_json(
            f"/Users/yagzanmanjunaath/UniWorkspace/ResearchMethods/Part2/ADSynth/generated_datasets/experiment_i_perm_{base_filename}.json",
        )

        with open(
                f"/Users/yagzanmanjunaath/UniWorkspace/ResearchMethods/Part2/ADSynth/generated_datasets/mgm_i_perm_{base_filename}.json",
                "w") as f:
            json.dump(misconfig_metrics_per_itr, f, indent=4)

    def grp_permission_injection(self, args):
        if len(NODES) == 0:
            print("====================================================================")
            print("== No graph intialised to generate misconfigurations ==")
            return
        nTiers = get_num_tiers(self.parameters)

        num_users = get_int_param_value("User", "nUsers", self.parameters)

        num_computers = get_int_param_value("Computer", "nComputers", self.parameters)

        num_local_admin_groups = sum(len(subarray) for subarray in EXP_LOCAL_ADMINS)
        # 2 lists for ACL and non-ACL permissions
        # ACLs
        acl_permission_probs = get_dict_param_value("ACLs", "ACLsProbability", self.parameters)
        ACL_PERMISSIONS = get_acls_list(acl_permission_probs)

        # Non-ACLs
        non_acl_permission_probs = get_dict_param_value("nonACLs", "nonACLsProbability", self.parameters)
        NON_ACL_PERMISSIONS = get_non_acls_list(non_acl_permission_probs)

        logging.info("====================================================================")
        logging.info("== Injecting Group Permission Misconfigurations ==")
        logging.info("Num of Users %s", num_users)
        logging.info("Num of Computers %s", num_computers)

        N_baseline_grp_permission = get_baseline_from_AD("g_perm", ACL_PERMISSIONS + NON_ACL_PERMISSIONS)

        # ACL setup
        acl_ratio = get_perc_param_value("misconfig_group", "acl_ratio", self.parameters)
        admin_ratio = get_perc_param_value("misconfig_group", "admin_ratio", self.parameters)
        departments_probs = get_dict_param_value("Group", "departmentProbability", self.parameters)
        departments_list = get_departments_list(departments_probs)
        locations = get_locations(self.parameters)

        misconfig_perc = get_perc_param_value("perc_misconfig_permissions_on_groups", self.level, self.parameters) / 100
        num_misconfig = int(misconfig_perc * num_local_admin_groups)
        misconfig_to_tier_0_allow, misconfig_to_tier_0_limit = get_misconfig_dict_param_value(
            "misconfig_permissions_to_tier_0", self.parameters)

        high_value_target_name = "DOMAIN ADMINS@TESTLAB.LOCALE"

        misconfig_metrics_per_itr = {}

        base_filename = os.path.splitext(os.path.basename(self.parameters_json_path))[0]

        for itr in range(self.R):
            if args == "isolated":
                init_experiment_state()
            else:
                restore_experiment_state(itr)

            networkx_graph = create_networkx_graph()

            misconfig_growth_metrics = {}
            for misconfig_grp_permission_count in range(1, num_misconfig + 1):
                print(f"Injecting {misconfig_grp_permission_count}")
                logging.info(f"New Grp Permission {misconfig_grp_permission_count}")
                p = misconfig_grp_permission_count / N_baseline_grp_permission
                networkx_graph = create_misconfig_permissions_on_groups_from_entrypoints(self.domain,
                                                                                         nTiers,
                                                                                         self.level,
                                                                                         self.parameters,
                                                                                         num_local_admin_groups,
                                                                                         acl_ratio,
                                                                                         admin_ratio,
                                                                                         departments_list,
                                                                                         locations,
                                                                                         ACL_PERMISSIONS,
                                                                                         NON_ACL_PERMISSIONS,
                                                                                         misconfig_to_tier_0_allow,
                                                                                         misconfig_to_tier_0_limit,
                                                                                         itr,
                                                                                         networkx_graph
                                                                                         )
                # if misconfig_session_count % 600 == 0:
                networkx_graph = create_networkx_graph()
                find_user_count_with_path_to_DA(networkx_graph, high_value_target_name, misconfig_grp_permission_count,
                                                misconfig_growth_metrics)

                misconfig_growth_metrics[misconfig_grp_permission_count]["p"] = p
                misconfig_growth_metrics[misconfig_grp_permission_count]["X"] = exposure_X(
                    misconfig_growth_metrics[misconfig_grp_permission_count]["reachable_users_count"],
                    misconfig_growth_metrics[misconfig_grp_permission_count]["reachable_comps_count"], num_users,
                    num_computers)
                indicators_hci_csm_tbs(EXP_EDGES, misconfig_growth_metrics, misconfig_grp_permission_count, {2}, 1.0)
                pbcc_result = pbcc_bounded_bfs_footholds(networkx_graph, WS_TIERS[2], high_value_target_name)
                misconfig_growth_metrics[misconfig_grp_permission_count]["pbcc"] = pbcc_result["pbcc"]

                misconfig_growth_metrics = compute_delta_X(misconfig_growth_metrics)
                p_star = find_p_star(misconfig_growth_metrics)

                # corr = np.corrcoef(HCI, deltaX)[0,1]

                logging.info(
                    "step=%d users=%d comps=%d p=%.6f X=%.4f delta_X=%.6f p_star=%.6f HCI=%.4f CSM=%.4f TBS=%.4f PBCC=%.4f",
                    misconfig_grp_permission_count,
                    misconfig_growth_metrics[misconfig_grp_permission_count]["reachable_users_count"],
                    misconfig_growth_metrics[misconfig_grp_permission_count]["reachable_comps_count"],
                    misconfig_growth_metrics[misconfig_grp_permission_count]["p"],
                    misconfig_growth_metrics[misconfig_grp_permission_count]["X"],
                    misconfig_growth_metrics[misconfig_grp_permission_count].get("delta_X", 0.0),
                    p_star,
                    misconfig_growth_metrics[misconfig_grp_permission_count]["HCI"],
                    misconfig_growth_metrics[misconfig_grp_permission_count]["CSM"],
                    misconfig_growth_metrics[misconfig_grp_permission_count]["TBS"],
                    misconfig_growth_metrics[misconfig_grp_permission_count]["pbcc"]
                )
            number_of_misconfigs = sorted(misconfig_growth_metrics.keys())

            corr = compute_hub_correlation(misconfig_growth_metrics)
            logging.info("corr(HCI, ΔX) = %.4f", corr)

            HCI = []
            deltaX = []

            for m in misconfig_growth_metrics.values():
                if "delta_X" in m:
                    HCI.append(m["HCI"])
                    deltaX.append(m["delta_X"])

            if itr == self.R - 1 and not self.skip_plots:
                plot_plot_chart(
                    x_values=HCI,
                    y_values=deltaX,
                    x_label="HCI",
                    y_label="ΔX",
                    title="Hub Concurrency vs Exposure Jump (g_perm)",
                    additional_info={},
                    plot_type="scatter"
                )

            misconfig_metrics_per_itr[itr] = misconfig_growth_metrics
            save_experiment_state(itr)
            saveTofile(self, f"g_perm-{itr}-{base_filename}.json")
            # clear_exp_neo4j_db(self.driver.session())
            # update_graph_db_with_temp_file(self.driver.session(), f"misconfig-session-temp={itr}")
            # tabulate_experiment_results(self.driver.session(),misconfig_growth_metrics)
            if itr == 0:
                plot_metrics(num_users, num_computers, num_misconfig, base_filename, misconfig_growth_metrics)

        mu = compute_mu(misconfig_metrics_per_itr, "X")
        logging.info("Mu :%s", mu)

        sigma2 = compute_sigma2(misconfig_metrics_per_itr, "X")
        logging.info("Sigma2 :%s", sigma2)

        if not sigma2:
            logging.warning("Sigma2 is empty. Cannot compute p_star.")
            p_star = None
        else:
            p_star = max(sigma2, key=sigma2.get)
        logging.info("P* :%s", p_star)
        run_metrics = misconfig_metrics_per_itr[0]

        steps = sorted(run_metrics.keys())

        X_values = [run_metrics[s]["X"] for s in steps]

        ci = compute_mu_sigma_ci(X_values, 0.95)
        logging.info("CI :%s", ci)

        logging.info("====================================================================")
        if not self.skip_plots:
                plot_plot_chart(
                    x_values=list(mu.keys()),
                    y_values=list(mu.values()),
                    x_label="p",
                    y_label="μ(p)",
                    title="Mean Exposure vs Misconfiguration Level  (g_perm)",
                    additional_info={"R": self.R},
                    plot_type="line"
                )

                plot_plot_chart(
                    x_values=list(sigma2.keys()),
                    y_values=list(sigma2.values()),
                    x_label="p",
                    y_label="σ²(p)",
                    title="Exposure Variance vs Misconfiguration Level (g_perm)",
                    additional_info={"R": self.R},
                    plot_type="line"
                )

        save_all_experiment_states_to_json(
            f"/Users/yagzanmanjunaath/UniWorkspace/ResearchMethods/Part2/ADSynth/generated_datasets/experiment_g_perm_{base_filename}.json",
        )

        with open(
                f"/Users/yagzanmanjunaath/UniWorkspace/ResearchMethods/Part2/ADSynth/generated_datasets/mgm_g_perm_{base_filename}.json",
                "w") as f:
            json.dump(misconfig_metrics_per_itr, f, indent=4)


    def grp_nesting_injection(self, args):
        if len(NODES) == 0:
            print("====================================================================")
            print("== No graph intialised to generate misconfigurations ==")
            return
        nTiers = get_num_tiers(self.parameters)

        num_users = get_int_param_value("User", "nUsers", self.parameters)

        num_computers = get_int_param_value("Computer", "nComputers", self.parameters)

        num_local_admin_groups = sum(len(subarray) for subarray in EXP_LOCAL_ADMINS)
        misconfig_perc = get_perc_param_value("perc_misconfig_nesting_groups", self.level, self.parameters) / 100
        num_misconfig = int(misconfig_perc * num_local_admin_groups)

        logging.info("====================================================================")
        logging.info("== Injecting Group Nesting Misconfigurations ==")
        logging.info("Num of Users %s", num_users)
        logging.info("Num of Computers %s", num_computers)

        N_baseline_grp_nesting = get_baseline_from_AD("nesting", None)

        # Nesting setup
        departments_probs = get_dict_param_value("Group", "departmentProbability", self.parameters)
        departments_list = get_departments_list(departments_probs)
        locations = get_locations(self.parameters)

        misconfig_metrics_per_itr = {}
        base_filename = os.path.splitext(os.path.basename(self.parameters_json_path))[0]

        high_value_target_name = "DOMAIN ADMINS@TESTLAB.LOCALE"

        misconfig_metrics_per_itr = {}

        base_filename = os.path.splitext(os.path.basename(self.parameters_json_path))[0]

        for itr in range(self.R):
            if args == "isolated":
                init_experiment_state()
            else:
                restore_experiment_state(itr)

            networkx_graph = create_networkx_graph()

            misconfig_growth_metrics = {}
            for misconfig_grp_nesting_count in range(1, num_misconfig + 1):
                print(f"Injecting {misconfig_grp_nesting_count}")
                logging.info(f"New Nesting {misconfig_grp_nesting_count}")
                p = misconfig_grp_nesting_count / N_baseline_grp_nesting
                networkx_graph = create_misconfig_group_nesting_from_entrypoints(self.domain, nTiers, departments_list,
                                                                                 locations, num_misconfig,
                                                                                 networkx_graph)
                # if misconfig_session_count % 600 == 0:
                networkx_graph = create_networkx_graph()
                find_user_count_with_path_to_DA(networkx_graph, high_value_target_name, misconfig_grp_nesting_count,
                                                misconfig_growth_metrics)

                misconfig_growth_metrics[misconfig_grp_nesting_count]["p"] = p
                misconfig_growth_metrics[misconfig_grp_nesting_count]["X"] = exposure_X(
                    misconfig_growth_metrics[misconfig_grp_nesting_count]["reachable_users_count"],
                    misconfig_growth_metrics[misconfig_grp_nesting_count]["reachable_comps_count"], num_users,
                    num_computers)
                indicators_hci_csm_tbs(EXP_EDGES, misconfig_growth_metrics, misconfig_grp_nesting_count, {2}, 1.0)
                pbcc_result = pbcc_bounded_bfs_footholds(networkx_graph, WS_TIERS[2], high_value_target_name)
                misconfig_growth_metrics[misconfig_grp_nesting_count]["pbcc"] = pbcc_result["pbcc"]

                misconfig_growth_metrics = compute_delta_X(misconfig_growth_metrics)
                p_star = find_p_star(misconfig_growth_metrics)

                # corr = np.corrcoef(HCI, deltaX)[0,1]

                logging.info(
                    "step=%d users=%d comps=%d p=%.6f X=%.4f delta_X=%.6f p_star=%.6f HCI=%.4f CSM=%.4f TBS=%.4f PBCC=%.4f",
                    misconfig_grp_nesting_count,
                    misconfig_growth_metrics[misconfig_grp_nesting_count]["reachable_users_count"],
                    misconfig_growth_metrics[misconfig_grp_nesting_count]["reachable_comps_count"],
                    misconfig_growth_metrics[misconfig_grp_nesting_count]["p"],
                    misconfig_growth_metrics[misconfig_grp_nesting_count]["X"],
                    misconfig_growth_metrics[misconfig_grp_nesting_count].get("delta_X", 0.0),
                    p_star,
                    misconfig_growth_metrics[misconfig_grp_nesting_count]["HCI"],
                    misconfig_growth_metrics[misconfig_grp_nesting_count]["CSM"],
                    misconfig_growth_metrics[misconfig_grp_nesting_count]["TBS"],
                    misconfig_growth_metrics[misconfig_grp_nesting_count]["pbcc"]
                )
            number_of_misconfigs = sorted(misconfig_growth_metrics.keys())

            corr = compute_hub_correlation(misconfig_growth_metrics)
            logging.info("corr(HCI, ΔX) = %.4f", corr)

            HCI = []
            deltaX = []

            for m in misconfig_growth_metrics.values():
                if "delta_X" in m:
                    HCI.append(m["HCI"])
                    deltaX.append(m["delta_X"])

            if itr == self.R - 1:
                plot_plot_chart(
                    x_values=HCI,
                    y_values=deltaX,
                    x_label="HCI",
                    y_label="ΔX",
                    title="Hub Concurrency vs Exposure Jump (g_nesting)",
                    additional_info={},
                    plot_type="scatter"
                )

            misconfig_metrics_per_itr[itr] = misconfig_growth_metrics
            save_experiment_state(itr)
            saveTofile(self, f"g_nest-{itr}-{base_filename}.json")
            # clear_exp_neo4j_db(self.driver.session())
            # update_graph_db_with_temp_file(self.driver.session(), f"misconfig-session-temp={itr}")
            # tabulate_experiment_results(self.driver.session(),misconfig_growth_metrics)
            if itr == 0:
                plot_metrics(num_users, num_computers, num_misconfig, base_filename, misconfig_growth_metrics)

        mu = compute_mu(misconfig_metrics_per_itr, "X")
        logging.info("Mu :%s", mu)

        sigma2 = compute_sigma2(misconfig_metrics_per_itr, "X")
        logging.info("Sigma2 :%s", sigma2)

        if not sigma2:
            logging.warning("Sigma2 is empty. Cannot compute p_star.")
            p_star = None
        else:
            p_star = max(sigma2, key=sigma2.get)
        logging.info("P* :%s", p_star)
        run_metrics = misconfig_metrics_per_itr[0]

        steps = sorted(run_metrics.keys())

        X_values = [run_metrics[s]["X"] for s in steps]

        ci = compute_mu_sigma_ci(X_values, 0.95)
        logging.info("CI :%s", ci)

        logging.info("====================================================================")

        plot_plot_chart(
            x_values=list(mu.keys()),
            y_values=list(mu.values()),
            x_label="p",
            y_label="μ(p)",
            title="Mean Exposure vs Misconfiguration Level  (g_nest)",
            additional_info={"R": self.R},
            plot_type="line"
        )

        plot_plot_chart(
            x_values=list(sigma2.keys()),
            y_values=list(sigma2.values()),
            x_label="p",
            y_label="σ²(p)",
            title="Exposure Variance vs Misconfiguration Level (g_nest)",
            additional_info={"R": self.R},
            plot_type="line"
        )

        save_all_experiment_states_to_json(
            f"/Users/yagzanmanjunaath/UniWorkspace/ResearchMethods/Part2/ADSynth/generated_datasets/experiment_g_nest_{base_filename}.json",
        )

        with open(
                f"/Users/yagzanmanjunaath/UniWorkspace/ResearchMethods/Part2/ADSynth/generated_datasets/mgm_g_nest_{base_filename}.json",
                "w") as f:
            json.dump(misconfig_metrics_per_itr, f, indent=4)


def saveTofile(self, filename):
    with open(
            f"/Users/yagzanmanjunaath/UniWorkspace/ResearchMethods/Part2/ADSynth/generated_datasets/{filename}",
            "w") as f:
        for obj in EXP_NODES:
            obj["type"] = "node"
            # Use json.dumps() to convert the object to a JSON string without square brackets
            json_str = json.dumps(obj, separators=(',', ':'))
            # Write the JSON string to the file with a newline character
            f.write(json_str + '\n')

    # Open the file in append mode
    with open(
            f"/Users/yagzanmanjunaath/UniWorkspace/ResearchMethods/Part2/ADSynth/generated_datasets/{filename}",
            'a') as f:
        print(f"generated_datasets/{filename}")
        for obj in EXP_EDGES:
            # Use json.dumps() to convert the object to a JSON string without square brackets
            json_str = json.dumps(obj, separators=(',', ':'))
            # Write the JSON string to the file with a newline character
            f.write(json_str + '\n')


def do_load_neo4jFromJson(self, args):
    parts = args.split(maxsplit=3)

    filename = parts[0] if len(parts) > 0 else ""
    clear_exp_neo4j_db(self.driver.session())
    load_graph_from_file(self.driver.session(), filename)


def convert_keys(self, obj):
    # If dict → convert each key recursively
    if isinstance(obj, dict):
        new_dict = {}
        for k, v in obj.items():
            try:
                # Convert keys like "1", "2" → int(1), int(2)
                new_key = int(k) if str(k).isdigit() else k
            except (ValueError, TypeError):
                new_key = k
            new_dict[new_key] = self.convert_keys(v)
        return new_dict
    # If list → convert each element recursively
    elif isinstance(obj, list):
        return [self.convert_keys(x) for x in obj]
    # Otherwise leave primitive unchanged
    else:
        return obj


def do_tabulateJson(self, args):
    parts = args.split(maxsplit=3)

    filename = parts[0] if len(parts) > 0 else ""
    itr = int(parts[1] if len(parts) > 1 else 1)
    misconfig_type = parts[2] if len(parts) > 2 else 1

    with open(
            f"/Users/yagzanmanjunaath/UniWorkspace/ResearchMethods/Part2/ADSynth/generated_datasets/{filename}",
            "r") as f:
        misconfig_metrics_per_itr = json.load(f)

    misconfig_metrics_per_itr = self.convert_keys(misconfig_metrics_per_itr)

    if itr:
        tabulate_experiment_results(self.driver.session(), misconfig_metrics_per_itr[itr])
    elif itr == -1:
        for misconfig_growth_metrics in misconfig_metrics_per_itr:
            tabulate_experiment_results(self.driver.session(), misconfig_metrics_per_itr[misconfig_growth_metrics],
                                        misconfig_type)


def do_push_graph_from_file(self, args):
    parts = args.split(maxsplit=3)

    filename = parts[0] if len(parts) > 0 else ""

    abs_path = os.path.abspath(filename)
    escaped_path = abs_path.replace("'", "\\'")  # replace single quote with escaped single quote

    query = (
        "PROFILE CALL apoc.periodic.iterate("
        f"\"CALL apoc.import.json('{escaped_path}')\", "
        "\"RETURN 1\", {batchSize: $bs})"
    )

    # Run (pass batch size as a parameter)
    self.driver.session().run(query, bs=1000)


def do_load_experiment_state_graph_from_file(self, args):
    parts = args.split(maxsplit=3)

    filename = parts[0] if len(parts) > 0 else ""
    itr = int(parts[1]) if len(parts) > 0 else 1
    load_all_experiment_states_from_json(
        f"/Users/yagzanmanjunaath/UniWorkspace/ResearchMethods/Part2/ADSynth/generated_datasets/{filename}")

    restore_experiment_state(itr)


def do_load_iterations(self, args):
    parts = args.split(maxsplit=3)

    misconfig_type = parts[0] if len(parts) > 1 else ""

    experiment_file = parts[1] if len(parts) > 1 else ""
    mgm_file = parts[2] if len(parts) > 2 else ""
    itr = int(parts[4]) if len(parts) > 4 else 1
    basefile = parts[3] if len(parts) > 3 else "secure_1k.json"

    # load_neo4jFromJson session-2-secure_1k.json
    self.do_load_neo4jFromJson(f"{misconfig_type}-{itr}-{basefile}")

    # load_experiment_state_graph_from_file experiment_session_secure_1k.json 2
    self.do_load_experiment_state_graph_from_file(f"{experiment_file} {itr}")
    # tabulateJson mgm_session_secure_1k.json 2

    if misconfig_type == "session":
        self.do_tabulateJson(f"{mgm_file} {itr} session")
    elif misconfig_type == "permission-i":
        self.do_tabulateJson(f"{mgm_file} {itr} permission")
    elif misconfig_type == "permission-g":
        print(EXP_MISCONFIGURED_GRP_PERMISSION)
    else:
        print(EXP_MISCONFIGURED_GRP_NESTING)
