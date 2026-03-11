import os, json, argparse, sys, time, ROOT
import pandas as pd
import plot_functions_in_memory as plot_functions
from io import StringIO

def main(arguments):

    # input parameters
    parser = argparse.ArgumentParser(description='')
    parser.add_argument("-pl", f"--plot-list", type=str, required=True, help="plot list line")
    parser.add_argument("-po", f"--plot-output-folder", type=str, required=True, help="output folder for plots (already hadded hitos)")
    parser.add_argument("-n", f"--n-cpus", type=int, required=False, help="#cpus to use", default=12)

    args = parser.parse_args(arguments)

    # json_dict = json.load(open(args.detectors_json, "r"))
    # global_dict = json_dict["global"]

    print(f"args.plot_list: {args.plot_list}")
    if args.plot_list.strip() == "": return

    plotconf_df = pd.read_csv(args.plot_list, sep=",", comment='#', quotechar='"', engine='python')
    plotconf_df = plotconf_df.fillna("")

    print(plotconf_df)

    ROOT.gROOT.LoadMacro("root_logon.C")
    os.system(f"mkdir {args.plot_output_folder}")

    if not os.path.exists(f"{args.plot_output_folder}/index.php"):
        os.system(f"cp {args.plot_output_folder}/../index.php {args.plot_output_folder}/index.php")
    if not os.path.exists(f"{args.plot_output_folder}/jsroot_viewer.php"):
        os.system(f"cp {args.plot_output_folder}/../jsroot_viewer.php {args.plot_output_folder}/jsroot_viewer.php")

    plotconf_df.apply(lambda row: plot_functions.plot(row, None, f"{args.plot_output_folder}/", just_draw=True), axis=1)

    #chunk_size = (len(plotconf_df) + args.n_cpus - 1) // args.n_cpus  # ceil division
    #chunks = [(plotconf_df.iloc[i*chunk_size : (i+1)*chunk_size], None, args.plot_output_folder, {"just_draw": True}) for i in range(args.n_cpus)]
    #with Pool(args.n_cpus) as pool:
    #    pool.map(plot_functions.plot_chunk, chunks)
    #for chunk in chunks: plot_functions.plot_chunk(chunk)

if __name__ == '__main__':
    main(sys.argv[1:])
