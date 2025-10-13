import os, json, uproot, argparse, sys, time, ROOT
import awkward as ak
import numpy as np
import pandas as pd
import plot_functions_in_memory as plot_functions
from multiprocessing import Pool


def main(arguments):
    parser = argparse.ArgumentParser(description='')
    parser.add_argument("-i", f"--input-file", type=str, required=True, help="input file with reco tree")
    parser.add_argument("-r",  f"--run", type=str, required=True, help="run number")
    parser.add_argument("-s",  f"--spill", type=str, required=True, help="spill number")
    parser.add_argument("-p",  f"--plot-list", type=str, required=True, help="csv file with plot list")
    parser.add_argument("-po", f"--plot-output-folder", type=str, required=True, help="output folder for plots")
    parser.add_argument("-opt", f"--option", type=str, required=True, help="beam or laser")
    args = parser.parse_args(arguments)

    #read reco file
    file = uproot.open(args.input)
    reco_tree = file["tree"]
