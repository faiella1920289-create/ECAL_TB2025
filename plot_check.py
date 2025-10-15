import os, json, uproot, argparse, sys, time, ROOT
import awkward as ak
import numpy as np
import pandas as pd
import plot_functions_in_memory as plot_functions
from multiprocessing import Pool


def main(arguments):
    parser = argparse.ArgumentParser(description='')
    parser.add_argument("-i", f"--input-file", type=str, required=True, help="input file with reco tree")
    parser.add_argument("-p",  f"--plot-list", type=str, required=True, help="csv file with plot list")
    parser.add_argument("-po", f"--plot-output-folder", type=str, required=True, help="output folder for plots")
    args = parser.parse_args(arguments)

    #read reco file
    file = uproot.open(args.input_file)
    arrays = file["tree"].arrays(library="np")

    plotconf_df = pd.read_csv(args.plot_list, sep=",", comment='#', quotechar='"', engine='python')
    plotconf_df = plotconf_df.fillna("")
    ROOT.gROOT.LoadMacro("root_logon.C")
    # os.system(f"mkdir -p {args.plot_output_folder}")
    if not os.path.exists(f"{args.plot_output_folder}/index.php"):
        os.system(f"cp index.php {args.plot_output_folder}/index.php")
    if not os.path.exists(f"{args.plot_output_folder}/jsroot_viewer.php"):
        os.system(f"cp jsroot_viewer.php {args.plot_output_folder}/jsroot_viewer.php")
    plotconf_df.apply(lambda row: plot_functions.plot(row, arrays, args.plot_output_folder), axis=1)

if __name__ == "__main__":
    main(sys.argv[1:])
