import os, json, argparse, sys, time, ROOT
import pandas as pd
import plot_functions_in_memory as plot_functions

def main(arguments):

    # input parameters
    parser = argparse.ArgumentParser(description='')
    parser.add_argument("-pl", f"--plotlist", type=str, required=True, help="plot list file")
    parser.add_argument("-po", f"--plot-output-folder", type=str, required=True, help="output folder for plots (already hadded hitos)")

    args = parser.parse_args(arguments)

    json_dict = json.load(open(args.detectors_json, "r"))
    global_dict = json_dict["global"]


    plotconf_df = pd.read_csv(args.plot_list, sep=",", comment='#')
    plotconf_df = plotconf_df.fillna("")

    ROOT.gROOT.LoadMacro("root_logon.C")
    os.system(f"mkdir {args.plot_output_folder}")

    if not os.path.exists(f"{args.plot_output_folder}/index.php"):
        os.system(f"cp {args.plot_output_folder}/../index.php {args.plot_output_folder}/index.php")
    if not os.path.exists(f"{args.plot_output_folder}/jsroot_viewer.php"):
        os.system(f"cp {args.plot_output_folder}/../jsroot_viewer.php {args.plot_output_folder}/jsroot_viewer.php")

    plotconf_df.apply(lambda row: plot_functions.plot(row, None, f"{args.plot_output_folder}/", just_draw=True), axis=1)


if __name__ == '__main__':
    main(sys.argv[1:])
