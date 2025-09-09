import cmd
import os
import sys
import json

from adsynth.ADSynth import Messages
import time
from adsynth.adsynth_templates.default_config import DEFAULT_CONFIGURATIONS
from adsynth.helpers.getters import get_num_tiers

from adsynth.synthesizer.misconfig import create_misconfig_sessions, create_misconfig_sessions_multi_tiers
from adsynth.utils.parameters import get_int_param_value
from adsynth.utils.parameters import print_all_parameters
from adsynth.utils.data import get_names_pool, get_surnames_pool, get_parameters_from_json
from adsynth.utils.misconfig_utils import populate_admin_users

class MisconfigInjector(cmd.Cmd):

    def __init__(self):
        self.m = Messages()
        self.domain = "TESTLAB.LOCALE"
        self.current_time = int(time.time())
        self.NODES = []
        self.EDGES = []
        self.parameters_json_path = "DEFAULT"
        # todo Get params from user
        self.parameters = DEFAULT_CONFIGURATIONS 
        self.json_file_name = None
        self.json_path = None

        self.level = "High"

        cmd.Cmd.__init__(self)

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
                return True

    def do_inject_misconfig_sessions(self, args):
        print("Inside misconfig sessions")
        pass

    def do_load_AD_graph(self, args):
        print(
            "Please input the name of a JSON file in the folder 'generated_datasets' (excluding the file extension). Otherwise, provide the full path to your intended JSON file")

        dataset_name = input("Dataset to be imported: ")
        cwd = os.getcwd()
        self.json_file_name = f"{os.path.dirname(cwd)}/generated_datasets/{dataset_name}.json"
        print(self.json_file_name)
        if not os.path.exists(self.json_file_name):
            self.json_file_name = dataset_name
            if not os.path.exists(self.json_file_name):
                print("There is no such file.")
                return

        with open(self.json_file_name, "r") as f:
            for line in f:
                obj = json.loads(line)
                if obj["type"] == "node":
                    self.NODES.append(obj)
                elif obj["type"] == "relationship":
                    self.EDGES.append(obj)

        ADMIN_USERS = populate_admin_users(self.NODES)
        return

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

        json_path = self.m.input_default("Parameters JSON file (copy and paste the full path of your parameter JSON file)", self.parameters_json_path)
        self.parameters = get_parameters_from_json(json_path)
        if self.parameters == DEFAULT_CONFIGURATIONS:
            self.parameters_json_path = "DEFAULT"
        else:
            self.parameters_json_path = json_path

        print_all_parameters(self.parameters)

    def do_inject_session_misconfigs(self, args):
        if not self.is_AD_graph_loaded():
            return

        nTiers = get_num_tiers(self.parameters)
        num_users = get_int_param_value("User", "nUsers", self.parameters)

        # todo Change after getting Custom params
        # create_misconfig_sessions(nTiers, self.level,self.parameters, num_users)

        create_misconfig_sessions_multi_tiers(nTiers,self.level,self.parameters,num_users)
        return

    def is_AD_graph_loaded(self):
        if len(self.NODES) == 0 or len(self.EDGES) == 0:
            print("AD Graph is not loaded. Run `load_AD_graph` and run again")
            return False
        return True

    def do_exit(self, args):
        raise KeyboardInterrupt


def main():
    try:
        MisconfigInjector().cmdloop()
    except KeyboardInterrupt:
        print("Exiting ADSynth")
        sys.exit()


if __name__ == '__main__':
    main()
