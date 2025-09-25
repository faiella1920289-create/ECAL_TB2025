#!/bin/bash

# --- Check input parameters ---
if [ "$#" -ne 2 ]; then
    echo "Usage: $0 <run_number> <spill_number>"
    exit 1
fi

RUN=$1
SPILL=$2

PLOT_MAIN_FOLDER="plots/"

# --- Start global timer ---
start_time=$(date +%s)

# --- EBeTe compilation ---
(
    echo "Building EBeTe and unpacking run $RUN spill $SPILL..."
    cd EBeTe || { echo "EBeTe folder not found!"; exit 1; }
    make -j
    export LD_LIBRARY_PATH="$PWD/build:$LD_LIBRARY_PATH"
    echo "Unpacking run $RUN spill $SPILL with EBeTe..."
    ./h4_raw2root /eos/cms/store/group/dpg_ecal/comm_ecal/upgrade/testbeam/ECALTB_H4_Jul2023/EB/$RUN/$SPILL.raw \
                  $HOME/ECAL_TB2025/raw/${RUN}_${SPILL}_raw.root
)

# --- Reco and plotting ---
(
    echo "Running reconstruction and plotting..."
    #    source /cvmfs/sft.cern.ch/lcg/views/LCG_106/x86_64-el9-gcc13-opt/setup.sh
    source ferrari/bin/activate
    cd ECAL_TB2025 || exit
    python3 reco.py -i "raw/${RUN}_${SPILL}_raw.root" \
            -r "$RUN" \
            -s "$SPILL" \
            -ro /eos/user/m/mcampana/www/h4dqm \
            -ej ecal_conf.json \
            -mj mcp_conf.json \
            -d data_to_plot.csv \
            -p plot_list.csv \
            -po $PLOT_MAIN_FOLDER/run_$RUN/current_spill
            -hd "source hadd.sh $RUN plot_list.csv $SPILL $PLOT_MAIN_FOLDER &"
)

echo "All done!"
end_time=$(date +%s)
total_time=$((end_time - start_time))
echo "Total elapsed time: $total_time seconds."
