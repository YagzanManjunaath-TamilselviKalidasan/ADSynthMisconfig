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

import cmd
import getpass
import json
import logging
import os
import random
import time
import uuid
from calendar import error
from datetime import datetime
from pathlib import Path
from timeit import default_timer as timer

import matplotlib.pyplot as plt
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_curve, auc, precision_recall_curve, average_precision_score
from sklearn.model_selection import train_test_split

import adsynth.DATABASE as DB
from adsynth.DATABASE import *
from adsynth.EXPERIMENT_DATABASE import EXP_ADMIN_USERS, EXP_ENABLED_USERS, EXP_LOCAL_ADMINS, \
    EXP_NODES, EXP_EDGES, EXP_MISCONFIGURED_GRP_PERMISSION, EXP_MISCONFIGURED_GRP_NESTING
from adsynth.adsynth_templates.default_config import DEFAULT_CONFIGURATIONS
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
from adsynth.utils.ablation_study_utils import indicators_hci_csm_tbs, exposure_X, populate_node_tiers, compute_mu, \
    compute_sigma2, \
    compute_delta_X, exposure_users, exposure_computers, pbcc_bounded_bfs_tier2_computers_debug, rows_from_run_metrics, \
    compute_rise_metrics, build_tier_caches
from adsynth.utils.data import get_names_pool, get_surnames_pool, get_parameters_from_json, get_domains_pool
from adsynth.utils.database_utils import init_experiment_state, restore_experiment_state, save_experiment_state, \
    clear_exp_neo4j_db, update_graph_db_with_temp_file, save_all_experiment_states_to_json, load_graph_from_file, \
    load_all_experiment_states_from_json
from adsynth.utils.domains import get_domain_dn
from adsynth.utils.misconfig_utils import tabulate_experiment_results
from adsynth.utils.mitigation_utils import run_cost_aware_mitigation_from_metrics
from adsynth.utils.networkx_utils import create_networkx_graph, find_user_count_with_path_to_DA
from adsynth.utils.online_mitigation_utils import apply_online_mitigation_if_triggered
from adsynth.utils.parameters import print_all_parameters, get_int_param_value, get_perc_param_value, \
    get_dict_param_value
from adsynth.utils.plot_utils import plot_plot_chart, export_experiment_to_duckdb_and_csv, \
    analyse_percolation_from_duckdb
from adsynth.utils.prediction_utils import calc_thresholds_and_jump_labels_for_iteration


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

        self.experiment_id = ""
        self.seed_number = None
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
        self.mitigation_enabled = False

        # R realizations - iterations as of now
        self.R = 20
        cmd.Cmd.__init__(self)
        logging.basicConfig(
            filename="app.log",
            level=logging.INFO,
            format="%(message)s"
        )

        logging.disable(logging.CRITICAL)

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
        if self.seed_number is None:
            seed_number = get_single_int_param_value("seed", self.parameters)
            if seed_number > 0:
                random.seed(seed_number)
            self.seed_number = seed_number
        else:
            if self.seed_number > 0:
                random.seed(self.seed_number)

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
        build_tier_caches()

    DATA_COLLECTION_SEEDS = [290]

    DATA_COLLECTION_VARIANTS = {
        "with_misconfig": True,
        # "without_misconfig": False,
    }

    DATA_COLLECTION_GRAPHS = {
        # "set_1": {
        #     "vul_1k": "/Users/yagzanmanjunaath/UniWorkspace/ResearchMethods/Part2/ADSynth/adsynth/experiment_params/vul_1k.json",
        #     "secure_1k": "/Users/yagzanmanjunaath/UniWorkspace/ResearchMethods/Part2/ADSynth/adsynth/experiment_params/secure_1k.json",
        # },
        "set_2": {
            # "vul_5k": "/Users/yagzanmanjunaath/UniWorkspace/ResearchMethods/Part2/ADSynth/adsynth/experiment_params/vul_5k.json",
            # "secure_5k": "/Users/yagzanmanjunaath/UniWorkspace/ResearchMethods/Part2/ADSynth/adsynth/experiment_params/secure_5k.json",
        },
        "set_3": {
            "vul_100k": "/Users/yagzanmanjunaath/UniWorkspace/ResearchMethods/Part2/ADSynth/adsynth/experiment_params/vul_100k.json",
            # "secure_100k": "/Users/yagzanmanjunaath/UniWorkspace/ResearchMethods/Part2/ADSynth/adsynth/experiment_params/secure_100k.json",
        },
    }

    DATA_COLLECTION_SCHEDULES = {
        # "session": ["session"],
        # "session_permission": ["session", "i_perm", "g_perm"],
        "session_permission_nesting": ["session", "i_perm", "g_perm", "nesting"],
    }

    def run_data_collection(self):
        """
        Runs:
        - Set 1: Vul 1K, Secure 1K
        - Set 2: Vul 5K, Secure 5K
        - Seeds: 1, 2, 4, 8, 16
        - Variants: with / without initial misconfig
        - Schedules:
            1. Session
            2. Session + Permission
            3. Session + Permission + Nesting
        """

        for set_name, graph_paths in self.DATA_COLLECTION_GRAPHS.items():
            for graph_name, json_path in graph_paths.items():
                for seed in self.DATA_COLLECTION_SEEDS:
                    for variant_name, misconfig_enabled in self.DATA_COLLECTION_VARIANTS.items():
                        for schedule_name, run_sequence in self.DATA_COLLECTION_SCHEDULES.items():
                            print("=" * 80)
                            print(f"Set              : {set_name}")
                            print(f"Graph            : {graph_name}")
                            print(f"JSON             : {json_path}")
                            print(f"Seed             : {seed}")
                            print(f"Initial variant  : {variant_name}")
                            print(f"Schedule         : {schedule_name}")
                            print(f"Run sequence     : {run_sequence}")
                            print("=" * 80)

                            self.seed_number = seed
                            self.misconfig_enabled = misconfig_enabled

                            self.do_initialise_AD_graph_from_json(
                                f"{json_path} {self.level}"
                            )

                            self.experiment_id = (
                                f"exp_{graph_name}_{variant_name}_{schedule_name}_"
                                f"seed_{seed}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                            )

                            self.experiment_name = (
                                f"{graph_name} | {variant_name} | "
                                f"{schedule_name} | seed={seed}"
                            )

                            self.run_injection_schedule(
                                schedule_type="sequence",
                                mitigation_enabled=False,
                                run_sequence=run_sequence
                            )

    def do_collect_data(self, args):
            self.run_data_collection()
    def do_isolated_injection(self, args):
        injection_type = input("Injection Type [session/i_perm/g_perm/nesting]  : ")
        args = "isolated"

        if injection_type == "session":
            self.session_injection(args)
        elif injection_type == "i_perm":
            self.indi_permission_injection(args)

    def run_injection_schedule(self, schedule_type, mitigation_enabled,run_sequence=None):
        self.mitigation_enabled = mitigation_enabled
        if run_sequence is None:
            run_sequence = []
        if schedule_type == "isolated":
            if run_sequence and len(run_sequence) == 1 and run_sequence[0] in ["session", "i_perm", "g_perm",
                                                                               "nesting"]:
                self.run_single_injection(run_sequence[0], schedule_type)

        elif schedule_type == "mixed":
            self.experiment_id = f"exp_mixed_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            self.experiment_name = "Mixed misconfiguration experiment"
            self.session_injection("mixed")
            self.indi_permission_injection("mixed")
            self.grp_permission_injection("mixed")
            self.grp_nesting_injection("mixed")
        elif schedule_type == "sequence":
            for injection_type in run_sequence:
                self.run_single_injection(injection_type, schedule_type)

    def run_single_injection(self, injection_type, mode):

        if injection_type == "session":
            if mode == "isolated":
                self.experiment_id = f"exp_session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                self.experiment_name = "Session misconfiguration experiment"
            self.session_injection(mode)
        elif injection_type == "i_perm":
            if mode == "isolated":
                self.experiment_id = f"exp_i_perm_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                self.experiment_name = "Individual permission misconfiguration experiment"
            self.indi_permission_injection(mode)
        elif injection_type == "g_perm":
            if mode == "isolated":
                self.experiment_id = f"exp_g_perm_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                self.experiment_name = "Group permission misconfiguration experiment"
            self.grp_permission_injection(mode)
        elif injection_type == "nesting":
            if mode == "isolated":
                self.experiment_id = f"exp_nesting_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                self.experiment_name = "Group nesting misconfiguration experiment"
            self.grp_nesting_injection(mode)

    def do_runmodels(self, args):

        passed = args

        if passed != "":
            try:
                csv_folder = passed

                self.run_all_csvs(
                    folder_path=csv_folder,
                    label_col="J_k5_z2p0",
                    threshold=0.5
                )

                return

            except ValueError:
                pass

        csv_folder = self.m.input_default(
            "CSV folder path",
            "analysis/csv"
        )

        self.run_all_csvs(
            folder_path=csv_folder,
            label_col="J_k5_z2p0",
            threshold=0.5
        )
    def run_all_csvs(
            self,
            folder_path,
            label_col="J_k5_z2p0",
            threshold=0.5
    ):
        folder = Path(folder_path)

        csv_files = sorted(folder.glob("*.csv"))

        if not csv_files:
            print("No CSV files found")
            return

        for csv_path in csv_files:

            print("=" * 80)
            print(f"Running: {csv_path.name}")
            print("=" * 80)

            try:
                self.run_model_suite_from_csv(
                    csv_path=str(csv_path),
                    label_col=label_col,
                    threshold=0.5,
                    generate_plots = False
                )

                print(f"Completed: {csv_path.name}")

            except Exception as e:
                print(f"Failed: {csv_path.name}")
                print(e)
    def run_model_suite_from_csv(
            self,
            csv_path,
            label_col="J_k5_z2p0",
            out_dir="analysis/plots",
            db_path=str(Path.home() / "adsynth_metrics.duckdb"),
            threshold=0.5,
            generate_plots=False
    ):
        import os
        import pandas as pd
        import matplotlib.pyplot as plt
        import duckdb

        from sklearn.model_selection import train_test_split
        from sklearn.linear_model import LogisticRegression
        from sklearn.metrics import (
            roc_curve,
            auc,
            precision_recall_curve,
            average_precision_score,
            roc_auc_score,
            precision_score,
            recall_score,
            f1_score,
            accuracy_score,
            confusion_matrix
        )

        os.makedirs(out_dir, exist_ok=True)

        df = pd.read_csv(csv_path)
        if "experiment_id" not in df.columns:
            raise ValueError("experiment_id column missing in CSV")

        experiment_id = df["experiment_id"].iloc[0]
        base_name = os.path.splitext(os.path.basename(csv_path))[0]

        model_specs = {
            # Single feature models
            "M1_HCI_only": ["HCI"],
            "M2_CSM_only": ["CSM"],
            "M3_TBS_only": ["TBS"],
            "M4_PBCC_only": ["PBCC"],

            # Two-feature combinations
            "M5_HCI_CSM": ["HCI", "CSM"],
            "M6_HCI_TBS": ["HCI", "TBS"],
            "M7_HCI_PBCC": ["HCI", "PBCC"],
            "M8_CSM_TBS": ["CSM", "TBS"],
            "M9_CSM_PBCC": ["CSM", "PBCC"],
            "M10_TBS_PBCC": ["TBS", "PBCC"],

            # Three-feature combinations
            "M11_HCI_CSM_TBS": ["HCI", "CSM", "TBS"],
            "M12_HCI_CSM_PBCC": ["HCI", "CSM", "PBCC"],
            "M13_HCI_TBS_PBCC": ["HCI", "TBS", "PBCC"],
            "M14_CSM_TBS_PBCC": ["CSM", "TBS", "PBCC"],

            # Full combination
            "M15_all": ["HCI", "CSM", "TBS", "PBCC"],
        }
        valid_df = df[df[label_col].notna()].copy()
        valid_df[label_col] = valid_df[label_col].astype(int)
        if generate_plots:
            fig_roc, ax_roc = plt.subplots(figsize=(8, 6))
            fig_pr, ax_pr = plt.subplots(figsize=(8, 6))

        metrics_rows = []
        prediction_rows = []

        for model_name, feature_cols in model_specs.items():

            use_cols = [c for c in feature_cols if c in valid_df.columns]

            if not use_cols:
                metrics_rows.append({
                    "experiment_id": experiment_id,
                    "model_name": model_name,
                    "features": ", ".join(feature_cols),
                    "status": "skipped_no_features"
                })
                continue

            model_df = valid_df.dropna(subset=use_cols + [label_col]).copy()

            if model_df.empty or model_df[label_col].nunique() < 2:
                metrics_rows.append({
                    "experiment_id": experiment_id,
                    "model_name": model_name,
                    "features": ", ".join(use_cols),
                    "status": "skipped_one_class_or_empty"
                })
                continue

            X = model_df[use_cols].values
            y = model_df[label_col].values

            X_train, X_test, y_train, y_test, idx_train, idx_test = train_test_split(
                X,
                y,
                model_df.index,
                test_size=0.3,
                random_state=42,
                stratify=y
            )

            clf = LogisticRegression(max_iter=2000)
            clf.fit(X_train, y_train)

            y_prob = clf.predict_proba(X_test)[:, 1]
            best_threshold = threshold


            precisions, recalls, thresholds = precision_recall_curve(
                    y_test,
                    y_prob
                )

            best_f1 = -1

            for t in thresholds:

                temp_pred = (y_prob >= t).astype(int)

                temp_f1 = f1_score(
                    y_test,
                    temp_pred,
                    zero_division=0
                )

                if temp_f1 > best_f1:
                    best_f1 = temp_f1
                    best_threshold = float(t)


            y_pred = (y_prob >= best_threshold).astype(int)

            test_eval_df = model_df.loc[idx_test].copy()
            test_eval_df["actual_label"] = y_test
            test_eval_df["predicted_label"] = y_pred
            test_eval_df["predicted_probability"] = y_prob

            lead_times = []
            detected_runs = 0
            total_jump_runs = 0

            group_cols = ["iteration_id"] if "iteration_id" in test_eval_df.columns else ["experiment_id"]

            for _, g in test_eval_df.sort_values("step").groupby(group_cols):
                actual_jumps = g[g["actual_label"] == 1]
                if actual_jumps.empty:
                    continue

                total_jump_runs += 1
                first_actual_jump_step = actual_jumps["step"].min()

                early_preds = g[
                    (g["predicted_label"] == 1) &
                    (g["step"] <= first_actual_jump_step)
                    ]

                if not early_preds.empty:
                    detected_runs += 1
                    first_pred_step = early_preds["step"].min()
                    lead_times.append(first_actual_jump_step - first_pred_step)

            avg_lead_time = sum(lead_times) / len(lead_times) if lead_times else None

            median_lead_time = (
                pd.Series(lead_times).median()
                if lead_times else None
            )

            detection_rate = (
                detected_runs / total_jump_runs
                if total_jump_runs > 0 else None
            )

            roc_auc = roc_auc_score(y_test, y_prob)
            pr_auc = average_precision_score(y_test, y_prob)

            precision = precision_score(y_test, y_pred, zero_division=0)
            recall = recall_score(y_test, y_pred, zero_division=0)
            f1 = f1_score(y_test, y_pred, zero_division=0)
            accuracy = accuracy_score(y_test, y_pred)

            tn, fp, fn, tp = confusion_matrix(y_test, y_pred).ravel()
            if generate_plots:
                fpr, tpr, _ = roc_curve(y_test, y_prob)
                ax_roc.plot(fpr, tpr, label=f"{model_name} (AUC={roc_auc:.3f})")

                pr_precision, pr_recall, _ = precision_recall_curve(y_test, y_prob)
                ax_pr.plot(pr_recall, pr_precision, label=f"{model_name} (AP={pr_auc:.3f})")

            metrics_rows.append({
                "experiment_id": experiment_id,
                "model_name": model_name,
                "features": ", ".join(use_cols),
                "label_col": label_col,
                "threshold": threshold,
                "status": "completed",

                "n_rows": len(model_df),
                "train_rows": len(y_train),
                "test_rows": len(y_test),

                "positive_rate_all": model_df[label_col].mean(),
                "positive_rate_test": y_test.mean(),

                "roc_auc": roc_auc,
                "pr_auc": pr_auc,
                "precision": precision,
                "recall": recall,
                "f1": f1,
                "accuracy": accuracy,

                "lead_time_avg": avg_lead_time,
                "lead_time_median": median_lead_time,
                "detection_rate": detection_rate,

                "tp": tp,
                "fp": fp,
                "tn": tn,
                "fn": fn,
            })

            for row_idx, actual, prob, pred in zip(idx_test, y_test, y_prob, y_pred):
                row = {
                    "experiment_id": experiment_id,
                    "model_name": model_name,
                    "source_row_index": int(row_idx),
                    "label_col": label_col,
                    "actual_label": int(actual),
                    "predicted_label": int(pred),
                    "predicted_probability": float(prob),
                    "threshold": threshold,
                }

                if "step" in model_df.columns:
                    row["step"] = model_df.loc[row_idx, "step"]

                if "p" in model_df.columns:
                    row["p"] = model_df.loc[row_idx, "p"]

                if "X" in model_df.columns:
                    row["X"] = model_df.loc[row_idx, "X"]

                prediction_rows.append(row)
        if generate_plots:

                ax_roc.plot([0, 1], [0, 1], linestyle="--")
                ax_roc.set_xlabel("False Positive Rate")
                ax_roc.set_ylabel("True Positive Rate")
                ax_roc.set_title(f"ROC Curves ({label_col})")
                ax_roc.legend()
                fig_roc.tight_layout()

                roc_path = os.path.join(out_dir, f"{experiment_id}_ROC.png")
                fig_roc.savefig(roc_path, dpi=300, bbox_inches="tight")

                baseline = valid_df[label_col].mean() if len(valid_df) else 0
                ax_pr.axhline(baseline, linestyle="--", label=f"Baseline={baseline:.3f}")
                ax_pr.set_xlabel("Recall")
                ax_pr.set_ylabel("Precision")
                ax_pr.set_title(f"PR Curves ({label_col})")
                ax_pr.legend()
                fig_pr.tight_layout()

                pr_path = os.path.join(out_dir, f"{experiment_id}_PR.png")
                fig_pr.savefig(pr_path, dpi=300, bbox_inches="tight")

        metrics_df = pd.DataFrame(metrics_rows)
        predictions_df = pd.DataFrame(prediction_rows)

        if generate_plots:
                plot_df = pd.DataFrame([{
                    "experiment_id": experiment_id,
                    "label_col": label_col,
                    "roc_plot_path": roc_path,
                    "pr_plot_path": pr_path,
                    "source_csv": csv_path,
                }])
        try:
            import duckdb

            con = duckdb.connect(db_path)

            # Register pandas DataFrames as DuckDB views
            con.register("metrics_df_view", metrics_df)
            con.register("predictions_df_view", predictions_df)
            if generate_plots:
                con.register("plot_df_view", plot_df)


            con.execute("""
                        CREATE TABLE IF NOT EXISTS prediction_model_metrics
                        (
                            experiment_id
                            VARCHAR,
                            model_name
                            VARCHAR,
                            features
                            VARCHAR,
                            label_col
                            VARCHAR,
                            threshold
                            DOUBLE,
                            status
                            VARCHAR,

                            n_rows
                            BIGINT,
                            train_rows
                            BIGINT,
                            test_rows
                            BIGINT,

                            positive_rate_all
                            DOUBLE,
                            positive_rate_test
                            DOUBLE,

                            roc_auc
                            DOUBLE,
                            pr_auc
                            DOUBLE,
                            precision
                            DOUBLE,
                            recall
                            DOUBLE,
                            f1
                            DOUBLE,
                            accuracy
                            DOUBLE,

                            lead_time_avg
                            DOUBLE,
                            lead_time_median
                            DOUBLE,
                            detection_rate
                            DOUBLE,

                            tp
                            BIGINT,
                            fp
                            BIGINT,
                            tn
                            BIGINT,
                            fn
                            BIGINT
                        )
                        """)

            con.execute("""
                        INSERT INTO prediction_model_metrics (experiment_id,
                                                              model_name,
                                                              features,
                                                              label_col,
                                                              threshold,
                                                              status,
                                                              n_rows,
                                                              train_rows,
                                                              test_rows,
                                                              positive_rate_all,
                                                              positive_rate_test,
                                                              roc_auc,
                                                              pr_auc,
                                                              precision,
                                                              recall,
                                                              f1,
                                                              accuracy,
                                                              lead_time_avg,
                                                              lead_time_median,
                                                              detection_rate,
                                                              tp,
                                                              fp,
                                                              tn,
                                                              fn,created_at)
                        SELECT experiment_id,
                               model_name,
                               features,
                               label_col,
                               threshold,
                               status,

                               n_rows,
                               train_rows,
                               test_rows,

                               positive_rate_all,
                               positive_rate_test,

                               roc_auc,
                               pr_auc, precision, recall, f1, accuracy, lead_time_avg, lead_time_median, detection_rate, tp, fp, tn, fn,CURRENT_TIMESTAMP
        
                        FROM metrics_df_view
                        """)

            con.execute("""
                        CREATE TABLE IF NOT EXISTS prediction_model_outputs
                        (
                            experiment_id
                            VARCHAR,
                            model_name
                            VARCHAR,
                            source_row_index
                            BIGINT,
                            label_col
                            VARCHAR,
                            actual_label
                            BIGINT,
                            predicted_label
                            BIGINT,
                            predicted_probability
                            DOUBLE,
                            threshold
                            DOUBLE,
                            step
                            BIGINT,
                            p
                            DOUBLE,
                            X
                            DOUBLE
                        )
                        """)

            if not predictions_df.empty:
                con.execute("""
                            INSERT INTO prediction_model_outputs (experiment_id,
                                                                  model_name,
                                                                  source_row_index,
                                                                  label_col,
                                                                  actual_label,
                                                                  predicted_label,
                                                                  predicted_probability,
                                                                  threshold,
                                                                  step,
                                                                  p,
                                                                  X)
                            SELECT experiment_id,
                                   model_name,
                                   source_row_index,
                                   label_col,
                                   actual_label,
                                   predicted_label,
                                   predicted_probability,
                                   threshold,
                        step,
                        p,
                        X
                    FROM predictions_df_view
                """)
            if generate_plots:
                    con.execute("""
                        CREATE TABLE IF NOT EXISTS prediction_plot_paths (
                            experiment_id VARCHAR,
                            label_col VARCHAR,
                            roc_plot_path VARCHAR,
                            pr_plot_path VARCHAR,
                            source_csv VARCHAR
                        )
                    """)

                    con.execute("""
                        INSERT INTO prediction_plot_paths (
                            experiment_id,
                            label_col,
                            roc_plot_path,
                            pr_plot_path,
                            source_csv
                        )
                        SELECT
                            experiment_id,
                            label_col,
                            roc_plot_path,
                            pr_plot_path,
                            source_csv
                        FROM plot_df_view
                    """)

            con.close()

        except Exception as e:
            print("DuckDB export failed:", e)

        if generate_plots:
                print(f"Saved ROC plot: {roc_path}")
                print(f"Saved PR plot: {pr_path}")
        print(f"Saved metrics to DuckDB: {db_path}")

        if generate_plots:
            plt.show()

        return metrics_df

    def session_injection(self, args):

        mode = "isolated"

        if args != "isolated":
            mode = "combined"
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

        # N_baseline_session = get_baseline_from_AD("session", None)
        N_baseline_session = num_users

        # Assuming Max of 10% of misconfigurations for fine grained analysis
        max_perc_misconfig_sessions = 0.1
        num_misconfig = int(max_perc_misconfig_sessions * num_users)
        high_value_target_name = "DOMAIN ADMINS@TESTLAB.LOCALE"

        misconfig_metrics_per_itr = {}

        base_filename = os.path.splitext(os.path.basename(self.parameters_json_path))[0]

        for itr in range(self.R):
            if mode == "isolated" or mode == "combined":
                init_experiment_state()
            else:
                restore_experiment_state(itr)
            # init_experiment_state()
            networkx_graph = create_networkx_graph()
            used_mitigation_cost = 0
            removed_mitigation_count = 0
            injection_family = "session"
            misconfig_growth_metrics = {}
            for misconfig_session_count in range(1, num_misconfig + 1):
                print(f"Injecting {misconfig_session_count}")
                logging.info(f"New Session {misconfig_session_count}")
                p = misconfig_session_count / N_baseline_session
                networkx_graph = create_misconfig_sessions_from_entrypoints_multi_tiers(nTiers, networkx_graph,
                                                                                        self.driver.session(),
                                                                                        misconfig_session_count,
                                                                                        self.level, self.parameters,misconfig_growth_metrics)

                networkx_graph = create_networkx_graph()
                find_user_count_with_path_to_DA(networkx_graph, high_value_target_name, misconfig_session_count,
                                                misconfig_growth_metrics)

                misconfig_growth_metrics[misconfig_session_count]["p"] = p
                misconfig_growth_metrics[misconfig_session_count]["X"] = exposure_X(
                    misconfig_growth_metrics[misconfig_session_count]["reachable_users_count"],
                    misconfig_growth_metrics[misconfig_session_count]["reachable_comps_count"], num_users,
                    num_computers)

                misconfig_growth_metrics[misconfig_session_count]["X_users"] = exposure_users(
                    misconfig_growth_metrics[misconfig_session_count]["reachable_users_count"], num_users)
                misconfig_growth_metrics[misconfig_session_count]["X_comps"] = exposure_computers(
                    misconfig_growth_metrics[misconfig_session_count]["reachable_comps_count"],
                    num_computers)

                indicators_hci_csm_tbs(EXP_EDGES, misconfig_growth_metrics, misconfig_session_count, num_users,
                                       DB.TOTAL_T0_USERS, {2},
                                       1.0)

                pbcc_result = pbcc_bounded_bfs_tier2_computers_debug(
                    networkx_graph,
                    high_value_target_name,
                    L=4,
                )
                if self.mitigation_enabled :
                            misconfig_growth_metrics, used_mitigation_cost, removed_mitigation_count = (
                                apply_online_mitigation_if_triggered(
                                    metrics=misconfig_growth_metrics,
                                    step=misconfig_session_count,
                                    p=p,
                                    injection_family=injection_family,
                                    high_value_target_name=high_value_target_name,
                                    num_users=num_users,
                                    num_computers=num_computers,
                                    mitigation_enabled=getattr(self, "mitigation_enabled", False),
                                    mitigation_condition=getattr(self, "mitigation_condition", None),
                                    mitigation_budget=getattr(self, "mitigation_budget", 100),
                                    used_cost=used_mitigation_cost,
                                    removed_count=removed_mitigation_count,
                                    rise_streak_k=getattr(self, "mitigation_rise_streak_k", 2),
                                )
                            )

                # print("PBCC:", pbcc_result["pbcc"])
                # print("Successful mixed paths:", pbcc_result["successful_paths"])
                # print("Path type counts:", pbcc_result["path_type_counts"])

                misconfig_growth_metrics[misconfig_session_count]["PBCC"] = pbcc_result["pbcc"]

                # corr = np.corrcoef(HCI, deltaX)[0,1]

                logging.info(
                    "step=%d users=%d comps=%d p=%.6f X=%.4f delta_X=%.6f HCI=%.4f CSM=%.4f TBS=%.4f PBCC=%.4f",
                    misconfig_session_count,
                    misconfig_growth_metrics[misconfig_session_count]["reachable_users_count"],
                    misconfig_growth_metrics[misconfig_session_count]["reachable_comps_count"],
                    misconfig_growth_metrics[misconfig_session_count]["p"],
                    misconfig_growth_metrics[misconfig_session_count]["X"],
                    misconfig_growth_metrics[misconfig_session_count].get("delta_X", 0.0),
                    misconfig_growth_metrics[misconfig_session_count]["HCI"],
                    misconfig_growth_metrics[misconfig_session_count]["CSM"],
                    misconfig_growth_metrics[misconfig_session_count]["TBS"],
                    misconfig_growth_metrics[misconfig_session_count]["PBCC"]
                )

            misconfig_growth_metrics = compute_delta_X(misconfig_growth_metrics)

            misconfig_growth_metrics = compute_rise_metrics(
                misconfig_growth_metrics,
                metric_keys=("HCI", "CSM", "TBS"),
            )

            metrics_with_jump_label, thresholds, datasets = calc_thresholds_and_jump_labels_for_iteration(
                misconfig_growth_metrics,
                itr=itr,
                baseline_fraction=0.2,
                min_points=5,
            )
            misconfig_growth_metrics = {row["step"]: row for row in metrics_with_jump_label}
            misconfig_metrics_per_itr[itr] = misconfig_growth_metrics
            save_experiment_state(itr)
            # if itr == 0:
            # saveTofile(self, f"session-{itr}-{base_filename}.json")

            # run_df, run_csv_path = save_iteration_csv(run_rows, out_dir="analysis/csv", base_filename=base_filename,itr=itr, )
            # logging.info("Saved iteration CSV: %s", run_csv_path)

            # clear_exp_neo4j_db(self.driver.session())
            # update_graph_db_with_temp_file(self.driver.session(), f"misconfig-session-temp={itr}")

        all_rows = []
        for itr in sorted(misconfig_metrics_per_itr.keys()):
            all_rows.extend(
                rows_from_run_metrics(
                    misconfig_metrics_per_itr[itr],
                    itr=itr,
                    base_filename=base_filename,
                    seed_number=self.seed_number,
                    injection_type="session",
                    mode=mode,
                )
            )

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

        # max_delta = find_p_max_delta(misconfig_growth_metrics)

        logging.info("====================================================================")

        if not self.skip_plots:
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

        # save_all_experiment_states_to_json(
        #     f"/Users/yagzanmanjunaath/UniWorkspace/ResearchMethods/Part2/ADSynth/generated_datasets/experiment_session_{self.experiment_id}.json",
        # )

        chart_metadata = {"Injection": "session", "mode": "isolated", "base": base_filename,
                          "total_misconfigs": num_misconfig, "seed_number": self.seed_number, }

        initial_misconfig = "Y" if self.misconfig_enabled else "N"

        chart_metadata["initial_misconfig"] = initial_misconfig

        export_experiment_to_duckdb_and_csv(
            misconfig_metrics_per_itr=misconfig_metrics_per_itr,
            mu=mu,
            sigma2=sigma2,
            p_star=p_star,
            duckdb_path=str(Path.home() / "adsynth_metrics.duckdb"),
            main_csv_path=f"analysis/csv/{self.experiment_id}.csv",
            experiment_id=self.experiment_id,
            experiment_name=self.experiment_name,
            base_graph_id=base_filename,
            base_graph_name=base_filename,
            regime_id=self.level,
            seed_number=self.seed_number,
            injection_type="session",
            injection_schedule_name="session_injection",
            initial_misconfig=self.misconfig_enabled,
            mode=mode,
        )



        # Commenting for roc check
        # export_metrics_to_excel(misconfig_metrics_per_itr[0], xl_filename, x_axis="step", metadata=chart_metadata)

        # xl_filename = f"analysis/misconfig_metrics_{base_filename}_{initial_misconfig}_{self.seed_number}.xlsx"
        # export_single_run_analysis_sheet(misconfig_metrics_per_itr[0], xl_filename)

        # with open(
        #         f"/Users/yagzanmanjunaath/UniWorkspace/ResearchMethods/Part2/ADSynth/generated_datasets/mgm_session_{base_filename}.json",
        #         "w") as f:
        #     json.dump(misconfig_metrics_per_itr, f, indent=4)

    # Skipping log reg
    #         df_summary, df_coefs, df_coef_wide, df_skipped = run_logreg_all_iterations_to_excel(
    #             misconfig_metrics_per_itr,
    #             output_excel="analysis/logreg_all_iterations.xlsx",
    #             feature_cols=["HCI", "CSM", "TBS"],
    #             x_col="X",
    #             quantile=0.8,
    #         )
    #
    #         df_summary, df_coefs, df_coef_wide, df_skipped = run_logreg_all_iterations_to_excel(
    #             misconfig_metrics_per_itr,
    #             output_excel="analysis/logreg_all_iterations_rise.xlsx",
    #             feature_cols=[
    #                 "HCI", "CSM", "TBS",
    #                 "delta_HCI", "delta_CSM", "delta_TBS",
    #                 "rise_streak_HCI", "rise_streak_CSM", "rise_streak_TBS",
    #             ],
    #             x_col="X",
    #             quantile=0.8,
    #         )

    def indi_permission_injection(self, args):
        mode = "isolated"

        if args != "isolated":
            mode = "combined"
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

        # N_baseline_indi_permission = get_baseline_from_AD("i_perm", CP)
        N_baseline_indi_permission = num_users

        misconfig_perc = get_perc_param_value("perc_misconfig_permissions", self.level, self.parameters) / 100
        # num_misconfig = int(misconfig_perc * num_users)
        # num_misconfig = 10
        # num_misconfig = int(misconfig_perc * num_users)
        num_misconfig = int(0.001 * num_users)
        misconfig_to_tier_0_allow, misconfig_to_tier_0_limit = get_misconfig_dict_param_value(
            "misconfig_permissions_to_tier_0", self.parameters)

        misconfig_metrics_per_itr = {}

        high_value_target_name = "DOMAIN ADMINS@TESTLAB.LOCALE"

        misconfig_metrics_per_itr = {}

        base_filename = os.path.splitext(os.path.basename(self.parameters_json_path))[0]
        for itr in range(self.R):
            if mode == "isolated":
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

                misconfig_growth_metrics[misconfig_indi_permission_count]["X_users"] = exposure_users(
                    misconfig_growth_metrics[misconfig_indi_permission_count]["reachable_users_count"], num_users)
                misconfig_growth_metrics[misconfig_indi_permission_count]["X_comps"] = exposure_computers(
                    misconfig_growth_metrics[misconfig_indi_permission_count]["reachable_comps_count"],
                    num_computers)

                indicators_hci_csm_tbs(EXP_EDGES, misconfig_growth_metrics, misconfig_indi_permission_count, num_users,
                                       DB.TOTAL_T0_USERS, {2}, 1.0)
                pbcc_result = pbcc_bounded_bfs_tier2_computers_debug(
                    networkx_graph,
                    high_value_target_name,
                    L=4,
                )

                misconfig_growth_metrics[misconfig_indi_permission_count]["PBCC"] = pbcc_result["pbcc"]

                logging.info(
                    "step=%d users=%d comps=%d p=%.6f X=%.4f delta_X=%.6f HCI=%.4f CSM=%.4f TBS=%.4f PBCC=%.4f",
                    misconfig_indi_permission_count,
                    misconfig_growth_metrics[misconfig_indi_permission_count]["reachable_users_count"],
                    misconfig_growth_metrics[misconfig_indi_permission_count]["reachable_comps_count"],
                    misconfig_growth_metrics[misconfig_indi_permission_count]["p"],
                    misconfig_growth_metrics[misconfig_indi_permission_count]["X"],
                    misconfig_growth_metrics[misconfig_indi_permission_count].get("delta_X", 0.0),
                    misconfig_growth_metrics[misconfig_indi_permission_count]["HCI"],
                    misconfig_growth_metrics[misconfig_indi_permission_count]["CSM"],
                    misconfig_growth_metrics[misconfig_indi_permission_count]["TBS"],
                    misconfig_growth_metrics[misconfig_indi_permission_count]["PBCC"]
                )
            misconfig_growth_metrics = compute_delta_X(misconfig_growth_metrics)

            misconfig_growth_metrics = compute_rise_metrics(
                misconfig_growth_metrics,
                metric_keys=("HCI", "CSM", "TBS"),
            )

            metrics_with_jump_label, thresholds, datasets = calc_thresholds_and_jump_labels_for_iteration(
                misconfig_growth_metrics,
                itr=itr,
                baseline_fraction=0.2,
                min_points=5,
            )
            misconfig_growth_metrics = {row["step"]: row for row in metrics_with_jump_label}
            misconfig_metrics_per_itr[itr] = misconfig_growth_metrics
            save_experiment_state(itr)
            # saveTofile(self, f"indi_permission-{itr}-{base_filename}.json")

        all_rows = []
        for itr in sorted(misconfig_metrics_per_itr.keys()):
            all_rows.extend(
                rows_from_run_metrics(
                    misconfig_metrics_per_itr[itr],
                    itr=itr,
                    base_filename=base_filename,
                    seed_number=self.seed_number,
                    injection_type="individual_permission",
                    mode=mode,
                )
            )

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

        # max_delta = find_p_max_delta(misconfig_growth_metrics)

        logging.info("====================================================================")

        if not self.skip_plots:
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

        # save_all_experiment_states_to_json(
        #     f"/Users/yagzanmanjunaath/UniWorkspace/ResearchMethods/Part2/ADSynth/generated_datasets/experiment_i_perm_{self.experiment_id}.json",
        # )
        chart_metadata = {"Injection": "Individual permission", "mode": "isolated", "base": base_filename,
                          "total_misconfigs": num_misconfig, "seed_number": self.seed_number, }

        initial_misconfig = "Y" if self.misconfig_enabled else "N"

        chart_metadata["initial_misconfig"] = initial_misconfig

        export_experiment_to_duckdb_and_csv(
            misconfig_metrics_per_itr=misconfig_metrics_per_itr,
            mu=mu,
            sigma2=sigma2,
            p_star=p_star,
            duckdb_path=str(Path.home() / "adsynth_metrics.duckdb"),
            main_csv_path=f"analysis/csv/master_{self.experiment_id}.csv",
            experiment_id=self.experiment_id,
            experiment_name=self.experiment_name,
            base_graph_id=base_filename,
            base_graph_name=base_filename,
            regime_id=self.level,
            seed_number=self.seed_number,
            injection_type="permission",
            injection_schedule_name="individual_permission_injection",
            initial_misconfig=self.misconfig_enabled,
            mode=mode,
        )
        # with open(
        #         f"/Users/yagzanmanjunaath/UniWorkspace/ResearchMethods/Part2/ADSynth/generated_datasets/mgm_i_perm_{base_filename}.json",
        #         "w") as f:
        #     json.dump(misconfig_metrics_per_itr, f, indent=4)

    def grp_permission_injection(self, args):
        mode = "isolated"

        if args != "isolated":
            mode = "combined"
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

        # N_baseline_grp_permission = get_baseline_from_AD("g_perm", ACL_PERMISSIONS + NON_ACL_PERMISSIONS)
        N_baseline_grp_permission = num_local_admin_groups

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
            if mode == "isolated":
                init_experiment_state()
            else:
                restore_experiment_state(itr)

            networkx_graph = create_networkx_graph()

            misconfig_growth_metrics = {}
            if num_misconfig == 0:
                return
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

                misconfig_growth_metrics[misconfig_grp_permission_count]["X_users"] = exposure_users(
                    misconfig_growth_metrics[misconfig_grp_permission_count]["reachable_users_count"], num_users)
                misconfig_growth_metrics[misconfig_grp_permission_count]["X_comps"] = exposure_computers(
                    misconfig_growth_metrics[misconfig_grp_permission_count]["reachable_comps_count"],
                    num_computers)

                indicators_hci_csm_tbs(EXP_EDGES, misconfig_growth_metrics, misconfig_grp_permission_count, num_users,
                                       DB.TOTAL_T0_USERS, {2}, 1.0)
                pbcc_result = pbcc_bounded_bfs_tier2_computers_debug(
                    networkx_graph,
                    high_value_target_name,
                    L=4,
                )
                misconfig_growth_metrics[misconfig_grp_permission_count]["PBCC"] = pbcc_result["pbcc"]
                logging.info(
                    "step=%d users=%d comps=%d p=%.6f X=%.4f delta_X=%.6f HCI=%.4f CSM=%.4f TBS=%.4f PBCC=%.4f",
                    misconfig_grp_permission_count,
                    misconfig_growth_metrics[misconfig_grp_permission_count]["reachable_users_count"],
                    misconfig_growth_metrics[misconfig_grp_permission_count]["reachable_comps_count"],
                    misconfig_growth_metrics[misconfig_grp_permission_count]["p"],
                    misconfig_growth_metrics[misconfig_grp_permission_count]["X"],
                    misconfig_growth_metrics[misconfig_grp_permission_count].get("delta_X", 0.0),
                    misconfig_growth_metrics[misconfig_grp_permission_count]["HCI"],
                    misconfig_growth_metrics[misconfig_grp_permission_count]["CSM"],
                    misconfig_growth_metrics[misconfig_grp_permission_count]["TBS"],
                    misconfig_growth_metrics[misconfig_grp_permission_count]["PBCC"]
                )

            misconfig_growth_metrics = compute_delta_X(misconfig_growth_metrics)

            misconfig_growth_metrics = compute_rise_metrics(
                misconfig_growth_metrics,
                metric_keys=("HCI", "CSM", "TBS"),
            )

            metrics_with_jump_label, thresholds, datasets = calc_thresholds_and_jump_labels_for_iteration(
                misconfig_growth_metrics,
                itr=itr,
                baseline_fraction=0.2,
                min_points=5,
            )
            misconfig_growth_metrics = {row["step"]: row for row in metrics_with_jump_label}
            misconfig_metrics_per_itr[itr] = misconfig_growth_metrics
            save_experiment_state(itr)
            # saveTofile(self, f"grp_permission-{itr}-{base_filename}.json")

            # clear_exp_neo4j_db(self.driver.session())
            # update_graph_db_with_temp_file(self.driver.session(), f"misconfig-session-temp={itr}")

        all_rows = []
        for itr in sorted(misconfig_metrics_per_itr.keys()):
            all_rows.extend(
                rows_from_run_metrics(
                    misconfig_metrics_per_itr[itr],
                    itr=itr,
                    base_filename=base_filename,
                    seed_number=self.seed_number,
                    injection_type="group_permission",
                    mode=mode,
                )
            )

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
        logging.info("====================================================================")
        if not self.skip_plots:
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

        # save_all_experiment_states_to_json(
        #     f"/Users/yagzanmanjunaath/UniWorkspace/ResearchMethods/Part2/ADSynth/generated_datasets/experiment_g_perm_{self.experiment_id}.json",
        # )
        chart_metadata = {"Injection": "Group permission", "mode": "isolated", "base": base_filename,
                          "total_misconfigs": num_misconfig, "seed_number": self.seed_number, }

        initial_misconfig = "Y" if self.misconfig_enabled else "N"

        chart_metadata["initial_misconfig"] = initial_misconfig
        export_experiment_to_duckdb_and_csv(
            misconfig_metrics_per_itr=misconfig_metrics_per_itr,
            mu=mu,
            sigma2=sigma2,
            p_star=p_star,
            duckdb_path=str(Path.home() / "adsynth_metrics.duckdb"),
            main_csv_path=f"analysis/csv/master_{self.experiment_id}.csv",
            experiment_id=self.experiment_id,
            experiment_name=self.experiment_name,
            base_graph_id=base_filename,
            base_graph_name=base_filename,
            regime_id=self.level,
            seed_number=self.seed_number,
            injection_type="permission",
            injection_schedule_name="group_permission_injection",
            initial_misconfig=self.misconfig_enabled,
            mode=mode,
        )

        # with open(
        #         f"/Users/yagzanmanjunaath/UniWorkspace/ResearchMethods/Part2/ADSynth/generated_datasets/mgm_g_perm_{base_filename}.json",
        #         "w") as f:
        #     json.dump(misconfig_metrics_per_itr, f, indent=4)

    def grp_nesting_injection(self, args):
        mode = "isolated"

        if args != "isolated":
            mode = "combined"
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

        N_baseline_grp_nesting = num_local_admin_groups

        # Nesting setup
        departments_probs = get_dict_param_value("Group", "departmentProbability", self.parameters)
        departments_list = get_departments_list(departments_probs)
        locations = get_locations(self.parameters)

        high_value_target_name = "DOMAIN ADMINS@TESTLAB.LOCALE"

        misconfig_metrics_per_itr = {}

        base_filename = os.path.splitext(os.path.basename(self.parameters_json_path))[0]
        if num_misconfig == 0:
            return
        for itr in range(self.R):
            if mode == "isolated":
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
                networkx_graph = create_networkx_graph()
                find_user_count_with_path_to_DA(networkx_graph, high_value_target_name, misconfig_grp_nesting_count,
                                                misconfig_growth_metrics)

                misconfig_growth_metrics[misconfig_grp_nesting_count]["p"] = p
                misconfig_growth_metrics[misconfig_grp_nesting_count]["X"] = exposure_X(
                    misconfig_growth_metrics[misconfig_grp_nesting_count]["reachable_users_count"],
                    misconfig_growth_metrics[misconfig_grp_nesting_count]["reachable_comps_count"], num_users,
                    num_computers)

                misconfig_growth_metrics[misconfig_grp_nesting_count]["X_users"] = exposure_users(
                    misconfig_growth_metrics[misconfig_grp_nesting_count]["reachable_users_count"], num_users)
                misconfig_growth_metrics[misconfig_grp_nesting_count]["X_comps"] = exposure_computers(
                    misconfig_growth_metrics[misconfig_grp_nesting_count]["reachable_comps_count"],
                    num_computers)

                indicators_hci_csm_tbs(EXP_EDGES, misconfig_growth_metrics, misconfig_grp_nesting_count, num_users,
                                       DB.TOTAL_T0_USERS, {2}, 1.0)

                pbcc_result = pbcc_bounded_bfs_tier2_computers_debug(
                    networkx_graph,
                    high_value_target_name,
                    L=4,
                )
                misconfig_growth_metrics[misconfig_grp_nesting_count]["PBCC"] = pbcc_result["pbcc"]

                logging.info(
                    "step=%d users=%d comps=%d p=%.6f X=%.4f delta_X=%.6f HCI=%.4f CSM=%.4f TBS=%.4f PBCC=%.4f",
                    misconfig_grp_nesting_count,
                    misconfig_growth_metrics[misconfig_grp_nesting_count]["reachable_users_count"],
                    misconfig_growth_metrics[misconfig_grp_nesting_count]["reachable_comps_count"],
                    misconfig_growth_metrics[misconfig_grp_nesting_count]["p"],
                    misconfig_growth_metrics[misconfig_grp_nesting_count]["X"],
                    misconfig_growth_metrics[misconfig_grp_nesting_count].get("delta_X", 0.0),
                    misconfig_growth_metrics[misconfig_grp_nesting_count]["HCI"],
                    misconfig_growth_metrics[misconfig_grp_nesting_count]["CSM"],
                    misconfig_growth_metrics[misconfig_grp_nesting_count]["TBS"],
                    misconfig_growth_metrics[misconfig_grp_nesting_count]["PBCC"]
                )
            misconfig_growth_metrics = compute_delta_X(misconfig_growth_metrics)

            misconfig_growth_metrics = compute_rise_metrics(
                misconfig_growth_metrics,
                metric_keys=("HCI", "CSM", "TBS"),
            )

            metrics_with_jump_label, thresholds, datasets = calc_thresholds_and_jump_labels_for_iteration(
                misconfig_growth_metrics,
                itr=itr,
                baseline_fraction=0.2,
                min_points=5,
            )

            misconfig_growth_metrics = {row["step"]: row for row in metrics_with_jump_label}
            misconfig_metrics_per_itr[itr] = misconfig_growth_metrics
            save_experiment_state(itr)
            # saveTofile(self, f"grp_nesting-{itr}-{base_filename}.json")


        all_rows = []
        for itr in sorted(misconfig_metrics_per_itr.keys()):
            all_rows.extend(
                rows_from_run_metrics(
                    misconfig_metrics_per_itr[itr],
                    itr=itr,
                    base_filename=base_filename,
                    seed_number=self.seed_number,
                    injection_type="session",
                    mode=mode,
                )
            )

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

        logging.info("====================================================================")
        if not self.skip_plots:
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

        # save_all_experiment_states_to_json(
        #     f"/Users/yagzanmanjunaath/UniWorkspace/ResearchMethods/Part2/ADSynth/generated_datasets/experiment_g_nest_{self.experiment_id}.json",
        # )

        chart_metadata = {"Injection": "Group nesting", "mode": "isolated", "base": base_filename,
                          "total_misconfigs": num_misconfig, "seed_number": self.seed_number, }

        initial_misconfig = "Y" if self.misconfig_enabled else "N"

        chart_metadata["initial_misconfig"] = initial_misconfig

        export_experiment_to_duckdb_and_csv(
            misconfig_metrics_per_itr=misconfig_metrics_per_itr,
            mu=mu,
            sigma2=sigma2,
            p_star=p_star,
            duckdb_path=str(Path.home() / "adsynth_metrics.duckdb"),
            main_csv_path=f"analysis/csv/master_{self.experiment_id}.csv",
            experiment_id=self.experiment_id,
            experiment_name=self.experiment_name,
            base_graph_id=base_filename,
            base_graph_name=base_filename,
            regime_id=self.level,
            seed_number=self.seed_number,
            injection_type="nesting",
            injection_schedule_name="grp_nesting_injection",
            initial_misconfig=self.misconfig_enabled,
            mode=mode,
        )

        # with open(
        #         f"/Users/yagzanmanjunaath/UniWorkspace/ResearchMethods/Part2/ADSynth/generated_datasets/mgm_g_nest_{base_filename}.json",
        #         "w") as f:
        #     json.dump(misconfig_metrics_per_itr, f, indent=4)

    def run_cost_aware_mitigation_from_json(
            self,
            json_path,
            condition="sessions_only",
            budgets=(10, 25, 50, 100),
            x_star=0.5,
            fixed_p_values=(0.02, 0.05, 0.10),
            out_duckdb_path=None,
    ):

        if out_duckdb_path is None:
            out_duckdb_path = str(Path.home() / "adsynth_metrics.duckdb")

        return run_cost_aware_mitigation_from_metrics(
            self=self,
            filepath=json_path,
            condition=condition,
            budgets=budgets,
            x_star=x_star,
            fixed_p_values=fixed_p_values,
            out_duckdb_path=out_duckdb_path,
        )

    def do_load_neo4jFromJson(self, args):
        parts = args.split(maxsplit=3)

        filename = parts[0] if len(parts) > 0 else ""
        clear_exp_neo4j_db(self.driver.session())
        load_graph_from_file(self.driver.session(), filename)

    def do_analyse_percolation(self, args):
        analyse_percolation_from_duckdb(str(Path.home() / "adsynth_metrics.duckdb"),"analysis/csv","2026-06-03 12:00:00","2026-06-03 18:00:00")
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

