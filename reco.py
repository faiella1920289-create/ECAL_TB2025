import os, json, uproot, argparse, sys, time, ROOT
import awkward as ak
import numpy as np
import reco_functions
import pandas as pd
import plot_functions_in_memory as plot_functions


def retrieve_conf(filename):
  with open(filename, 'r') as f:
    json_dict = json.load(f)
    if json_dict["active_ch_list"] == None: json_dict["active_ch_list"] = slice(None)
  return json_dict


def main(arguments):
    # start time
    time_start = time.time()

    # input parameters
    parser = argparse.ArgumentParser(description='')
    parser.add_argument("-i", f"--input", type=str, required=True, help="input ROOT file with unpacked tree")
    parser.add_argument("-r", f"--run", type=str, required=True, help="run number")
    parser.add_argument("-s", f"--spill", type=str, required=True, help="spill number")
    parser.add_argument("-ro", f"--reco-output-dir", type=str, required=True, help="directory for reco output")
    parser.add_argument("-ej", f"--ecal-json", type=str, required=False, help="ecal reco configuration", default="ecal_conf.json")
    parser.add_argument("-mj", f"--mcp-json", type=str, required=False, help="mcp reco configuration", default="mcp_conf.json")
    parser.add_argument("-ct", f"--compression-type", type=str, required=False, help="mcp reco configuration", default="lz4")
    parser.add_argument("-d", f"--data", type=str, required=True, help="csv file with data to plot")
    parser.add_argument("-p", f"--plot-list", type=str, required=True, help="csv file with plot list (mcp and ecal)")
    parser.add_argument("-po", f"--plot-output-folder", type=str, required=True, help="output folder for plots")

    args = parser.parse_args(arguments)




    ecal_json_dict, mcp_json_dict = (retrieve_conf(filename) for filename in [args.ecal_json, args.mcp_json])

    # open input file
    file = uproot.open(args.input)
    tree = file["h4"]

    ecal_waves = tree["xtal_sample"].array(library="np")[:, ecal_json_dict["active_ch_list"], :]
    ecal_waves, is_valid, gain_is_1 = reco_functions.decode_ecal_waves(ecal_waves)

    mcp_waves = tree["dgtz_sample"].array(library="np")[:, mcp_json_dict["active_ch_list"], :]
    mcp_waves = 4096 - mcp_waves #must be inverted if the signal are with negative rising slope

    print(f"reading data, json and cl arguments took {-time_start +time.time():.1f}")

    time_ecal = time.time()
    mask_ecal, reco_dict_ecal = reco_functions.generic_reco(ecal_waves, "ecal", **ecal_json_dict["reco_conf"])
    print(f"ecal reco took {-time_ecal +time.time():.1f} s")

    time_mcp = time.time()
    mask_mcp, reco_dict_mcp = reco_functions.generic_reco(mcp_waves, "mcp", **mcp_json_dict["reco_conf"])
    print(f"mcp reco took {-time_mcp +time.time():.1f} s")

    time_hodo = time.time()
    reco_dict_hodo = {}
    mask_hodo = np.ones(mask_mcp.shape[0], dtype=bool) #to be generic
    coords_list = ["x1", "x2", "y1", "y2"]
    branches = tree.arrays(
        [f"hodo_{coord}_nclusters" for coord in coords_list] +
        [f"hodo_{coord}_pos" for coord in coords_list],
        library="ak"
    )

    for coord in coords_list:
        clus = branches[f"hodo_{coord}_nclusters"]
        pos = branches[f"hodo_{coord}_pos"]
        mask = (clus > 0)

        pos_first_cluster = ak.to_numpy(ak.where(mask, ak.firsts(pos), -999))
        mask_single_cluster = ak.to_numpy(clus == 1)
        average_all_clusters = ak.to_numpy(ak.where(mask, ak.sum(pos, axis=1) / clus, -999.0 ))

        reco_dict_hodo.update({
            f"hodo_{coord}_cl0_pos": pos_first_cluster,
            f"hodo_{coord}_single_cl_flag": mask_single_cluster,
            f"hodo_{coord}_avg_pos": average_all_clusters,
        })
    print(f"hodo reco took {-time_hodo +time.time():.1f} s")



    time_merge = time.time()
    mask_global = np.logical_and.reduce((mask_ecal, mask_mcp, mask_hodo)) #to be generic
    reco_dict = {}
    reco_dict.update(reco_dict_ecal)
    reco_dict.update(reco_dict_mcp)
    reco_dict.update(reco_dict_hodo)

    for key in reco_dict: reco_dict[key] = reco_dict[key][mask_global, ...]

    print(f"merging took {-time_merge + time.time():.1f} s")
    print(f"Total time elapsed for reco: {time.time() - time_start:.4f} s")



    time_plot = time.time()
    plotconf_df = pd.read_csv(args.plot_list, sep=",")
    plotconf_df = plotconf_df.fillna("")

    # os.system(f"cp index.php {outputfolder}")

    ROOT.gROOT.LoadMacro("root_logon.C")

    os.system(f"mkdir {args.plot_output_folder}/prova")
    plotconf_df.apply(lambda row: plot_functions.plot(row, reco_dict, f"{args.plot_output_folder}/prova"), axis=1)




    time_end = time.time()
    print(f"Time elapsed for plotting: {time_end - time_plot:.4f} s")

    time_write = time.time()

    branch_types = {k: (v.dtype, v.shape[1:]) for k, v in reco_dict.items()}
    compression_map = {"zlib": uproot.compression.ZLIB(level=1), "lz4": uproot.compression.LZ4(level=1), "none": None}
    with uproot.recreate(f"{args.reco_output_dir}/{args.run}_{args.spill}_reco.root", compression=compression_map[args.compression_type]) as f:
        tree = f.mktree("tree", branch_types)
        tree.extend(reco_dict)

    print(f"writing reco output took {-time_write + time.time():.1f} s")

if __name__ == '__main__':
    main(sys.argv[1:])
