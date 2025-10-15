import os, json, uproot, argparse, sys, time, ROOT
import awkward as ak
import numpy as np
import reco_functions
import pandas as pd
import plot_functions_in_memory as plot_functions
from multiprocessing import Pool


def main(arguments):
    print("Entered reco.py")
    # start time
    time_start = time.time()

    # input parameters
    parser = argparse.ArgumentParser(description='')
    parser.add_argument("-i",  f"--input", type=str, required=True, help="input ROOT file with unpacked tree")
    parser.add_argument("-r",  f"--run", type=str, required=True, help="run number")
    parser.add_argument("-s",  f"--spill", type=str, required=True, help="spill number")
    parser.add_argument("-ro", f"--reco-output-dir", type=str, required=True, help="directory for reco output")
    parser.add_argument("-j", f"--detectors-conf-json", type=str, required=False, help="detectors reco configuration", default="conf.json")
    parser.add_argument("-ct", f"--compression-type", type=str, required=False, help="mcp reco configuration", default="lz4")
    parser.add_argument("-p",  f"--plot-list", type=str, required=True, help="csv file with plot list")
    parser.add_argument("-po", f"--plot-output-folder", type=str, required=True, help="output folder for plots")
    parser.add_argument("-hd", f"--hadd-cmd", type=str, required=False, default="", help="command to hadd")
    parser.add_argument("-opt", f"--option", type=str, required=True, help="beam or laser")
    args = parser.parse_args(arguments)

    # read detectors configuration
    json_dict = json.load(open(args.detectors_conf_json, "r"))
    detectors_dict = json_dict["detectors"]
    mode = json_dict["global"]["spill_type"][args.option]
    opt = mode["option"]
    if opt is not None:
        for detector in opt:
            for conf in opt[detector]["reco_conf"]:
                detectors_dict[detector]["reco_conf"][conf] = opt[detector]["reco_conf"][conf]
    print(f"args + conf took {-time_start + time.time():.1f} s")

    # open input file
    time_open = time.time()
    file = uproot.open(args.input)
    tree = file[mode["tree_name"]]
    n_events = tree.num_entries
    print(f"Tree contains: {n_events} events")
    if n_events == 0:
      print("Tree contains 0 events -> exiting")
      sys.exit(0)

    print(f"open file took {-time_open + time.time():.1f} s")

    # reconstruction
    time_reco = time.time()
    reco_dict = {}
    for detector in detectors_dict:
        time_reco_det = time.time()
        if detector not in mode["detector_list"]: continue
        dd = detectors_dict[detector]

        reco_dict[detector], geo_dict, chid_dict = {}, None, None
        if dd["ch_map"] == None: active_ch_list = slice(None)
        elif isinstance(dd["ch_map"], str):
          map_df = pd.read_csv(dd["ch_map"])
          active_row_list = (map_df["type"] == detector).tolist()
          active_ch_list = (map_df["branch_ch"][map_df["type"] == detector]).tolist()
          chid_dict = {var: map_df[var].to_numpy()[active_row_list] for var in dd["chid_vars_list"]}
          if dd["geo_needed"]:
            geo_dict = {coord: map_df[coord].to_numpy()[active_row_list] for coord in ["ieta", "iphi"]}
        elif isinstance(dd["ch_map"], list):
          active_ch_list = dd["ch_map"]

        if dd["generic_reco"]:
            waves = tree[dd["waves_branch"]].array(library="np")[:, active_ch_list, :].astype(np.uint16)
            if dd["decode"]: waves, is_valid, gain_is_1 = reco_functions.decode_ecal_waves(waves)
            if dd["to_be_inverted"]: waves = 4096 - waves #must be inverted if the signal are with negative rising slope
            reco_dict[detector]["mask"], reco_dict[detector]["arrays"] = reco_functions.generic_reco(
              waves, detector, opt, id=chid_dict, geo_dict=geo_dict, **dd["reco_conf"]
            )
            print(f"{detector}, selected: {reco_dict[detector]['mask'].sum()} events")
        elif detector == "hodo":
            reco_dict[detector]["mask"], reco_dict[detector]["arrays"] = reco_functions.hodo_reco(tree, detector)
            print(f"{detector}, selected: {reco_dict[detector]['mask'].sum()} events")
        elif detector == "bcp":
            bcp_clk = tree[dd["waves_branch"]].array(library="np")[:, active_ch_list, :]
            reco_dict[detector]["mask"], reco_dict[detector]["arrays"] = reco_functions.bcp_reco(bcp_clk, detector)
            print(f"{detector}, selected: {reco_dict[detector]['mask'].sum()} events")
        print(""f"{detector} reco took {-time_reco_det + time.time():.1f} s")
    print(f"reco took: {-time_reco + time.time():.1f} s")

    # time run controller
    time_rc = tree["time_rc"].array(library="np")

    # add event number
    n_events = np.arange(reco_dict["ecal"]["mask"].shape[0])
    reco_dict["events"] = {"mask": np.ones((n_events.shape[0],), dtype=bool), "arrays": {"n_event": n_events}}

    # merging
    time_merge = time.time()
    mask_global, arrays = np.logical_and.reduce([reco_dict[detector]["mask"] for detector in reco_dict]), {}
    for detector in reco_dict: arrays.update(reco_dict[detector]["arrays"])
    for branch in arrays: arrays[branch] = arrays[branch][mask_global, ...]
    print(f"merging took {-time_merge + time.time():.1f} s")

    # plotting
    time_plot = time.time()
    n_cpus = 8
    plotconf_df = pd.read_csv(args.plot_list, sep=",", comment='#', quotechar='"', engine='python')
    plotconf_df = plotconf_df.fillna("")
    ROOT.gROOT.LoadMacro("root_logon.C")
    # os.system(f"mkdir -p {args.plot_output_folder}")
    if not os.path.exists(f"{args.plot_output_folder}/index.php"):
        os.system(f"cp {args.plot_output_folder}/../../index.php {args.plot_output_folder}/index.php")
    if not os.path.exists(f"{args.plot_output_folder}/jsroot_viewer.php"):
        os.system(f"cp {args.plot_output_folder}/../../jsroot_viewer.php {args.plot_output_folder}/jsroot_viewer.php")
    if not os.path.exists(f"{args.plot_output_folder}/../index.php"):
        os.system(f"cp {args.plot_output_folder}/../../index.php {args.plot_output_folder}/../index.php")
    if not os.path.exists(f"{args.plot_output_folder}/../jsroot_viewer.php"):
        os.system(f"cp {args.plot_output_folder}/../../jsroot_viewer.php {args.plot_output_folder}/../jsroot_viewer.php")
    plotconf_df.apply(lambda row: plot_functions.plot(row, arrays, args.plot_output_folder), axis=1)
    print(f"plotting current spill took: {-time_plot + time.time():.1f} s")

    os.system(args.hadd_cmd) #goes in parallel

    # writing
    time_write = time.time()
    branch_types = {k: (v.dtype, v.shape[1:]) for k, v in arrays.items()}
    compression_map = {"zlib": uproot.compression.ZLIB(level=1), "lz4": uproot.compression.LZ4(level=1), "none": None}
    with uproot.recreate(f"{args.reco_output_dir}/{args.run}_{args.spill}_reco.root", compression=compression_map[args.compression_type]) as f:
        tree = f.mktree("tree", branch_types)
        tree.extend(arrays)
    print(f"writing reco output took {-time_write + time.time():.1f} s")

    print("----------------- unpacking, reco and plotting single spill done -----------------")

if __name__ == '__main__':
    main(sys.argv[1:])
