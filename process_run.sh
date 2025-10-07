#!/bin/bash

# --- launch settings with dynamic beam|laser choice ---
# if [ "$#" -ne 2 ]; then
#     echo "Usage: $0 <run_number> <spill_number>"
#     exit 1
# fi
# RUN=$1
# SPILL=$(printf "%04d" $2)
# SPILL_NO=$((10#$SPILL))
# SPILL_LASER=10
# SPILL_REP=5
# OPT=$(($SPILL_NO % $SPILL_LASER))
# if [ "$OPT" -eq 0 ]; then
#     option="laser"
# else
#     option="beam"
# fi

# --- launch settings with beam|laser as input parameter ---
if [ "$#" -ne 3 ]; then
    echo "Usage: $0 <run_number> <spill_number> <beam|laser>"
    exit 1
fi
RUN=$1
SPILL=$(printf "%04d" $2)
SPILL_NO=$((10#$SPILL))
SPILL_LASER=10
SPILL_REP=5
option=$3

PLOT_MAIN_FOLDER="/eos/user/m/mcampana/www/h4dqm/ECAL_TB_2025"

WORKING_DIR=$(pwd)

# --- Start global timer ---
start_time=$(date +%s)

RECO_UNPACKED_OUTDIR="/eos/cms/store/group/dpg_ecal/comm_ecal/upgrade/testbeam/ECALTB_H4_Oct2025/"
mkdir -p ${RECO_UNPACKED_OUTDIR}/unpacked/run_$RUN/
UNPACKED_FILE="${RECO_UNPACKED_OUTDIR}/unpacked/run_$RUN/run_${RUN}_spill_${SPILL}_unpacked.root"

EBETE_DIR="/afs/cern.ch/user/e/ecalgit/EBeTe"
cd ${EBETE_DIR}

# --- EBeTe compilation ---
echo "Building EBeTe and unpacking run $RUN spill $SPILL..."
#make -j
export LD_LIBRARY_PATH="${EBETE_DIR}/build:$LD_LIBRARY_PATH"
echo "Unpacking run $RUN spill $SPILL with EBeTe..."
echo "./h4_raw2root /eos/cms/store/group/dpg_ecal/comm_ecal/upgrade/testbeam/ECALTB_H4_Jul2023/EB/$RUN/$SPILL.raw ${UNPACKED_FILE}"
./h4_raw2root /eos/cms/store/group/dpg_ecal/comm_ecal/upgrade/testbeam/ECALTB_H4_Jul2023/EB/$RUN/$SPILL.raw ${UNPACKED_FILE}

mkdir -p ${RECO_UNPACKED_OUTDIR}/reco/run_$RUN/
mkdir $PLOT_MAIN_FOLDER/run_$RUN/
mkdir $PLOT_MAIN_FOLDER/run_$RUN/current_spill/

cd $WORKING_DIR

/bin/cp *.php $PLOT_MAIN_FOLDER

# --- Reco and plotting ---
echo "Running reconstruction and plotting..."
#source /cvmfs/sft.cern.ch/lcg/views/LCG_106/x86_64-el9-gcc13-opt/setup.sh
source ${HOME}/ferrari/bin/activate
# python3 reco_old.py -i ${UNPACKED_FILE} \
#     -r "$RUN" \
#     -s "$SPILL" \
#     -ro ${RECO_UNPACKED_OUTDIR}/reco/run_$RUN/ \
#     -ej ecal_conf.json \
#     -mj mcp_conf.json \
#     -p plotlists/plot_list.csv \
#     -po $PLOT_MAIN_FOLDER/run_$RUN/current_spill/ \
#     -hd "source ${WORKING_DIR}/hadd.sh $RUN plot_list.csv $SPILL $PLOT_MAIN_FOLDER &"

python3 reco.py -i ${UNPACKED_FILE} \
    -r "$RUN" \
    -s "$SPILL" \
    -ro ${RECO_UNPACKED_OUTDIR}/reco/run_$RUN/ \
    -j detectors_conf.json \
    -p plotlists/plot_list_$option.csv \
    -po $PLOT_MAIN_FOLDER/run_$RUN/current_spill/ \
    -hd "source ${WORKING_DIR}/hadd.sh $RUN plotlists/plot_list_$option.csv $SPILL $PLOT_MAIN_FOLDER &" \
    -opt $option

echo "----------------- unpacking, reco and plotting single spill done -----------------"
end_time=$(date +%s)
total_time=$((end_time - start_time))
echo "Total elapsed time: $total_time seconds."

# --- Saving plot for selected spills ---
if [ "$SPILL_NO" -lt "$SPILL_REP" ] || [ $((SPILL_NO % SPILL_LASER)) -eq 0 ] || [ $((SPILL_NO % SPILL_REP)) -eq $((SPILL_REP - 1)) ]; then
    echo ">>> Spill $SPILL selezionato, salvo anche in $PLOT_MAIN_FOLDER/run_$RUN/spill_$SPILL <<<"
    cp -rT "$PLOT_MAIN_FOLDER/run_$RUN/current_spill" "$PLOT_MAIN_FOLDER/run_$RUN/spill_$SPILL"
fi
