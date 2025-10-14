__all__ = ()

import sys
from adsynth.ADSynth import MainMenu


def main():
    try:

        main = MainMenu()
        args = "/Users/yagzanmanjunaath/UniWorkspace/ResearchMethods/CodeSpace/ADSynth/adsynth/experiment_params/secure_1k.json  High"
        main.do_initialise_AD_graph_from_json(args)
        main.do_inject_session_misconfigs(args)

    except KeyboardInterrupt:
        print("Exiting ADSynth")
        sys.exit()

if __name__ == '__main__':
    main()
