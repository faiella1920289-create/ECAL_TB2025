#!/bin/bash

# --- launch settings with beam|laser as input parameter ---
if [ "$#" -ne 3 ]; then
    echo "Usage: $0 <run_number> <spill_number> <beam|laser|beam+laser>"
    exit 1
fi
RUN=$1
SPILL=$(printf "%04d" $((10#$2)))
SPILL_NO=$((10#$SPILL))
SPILL_LASER=10
SPILL_REP=5
beam_or_laser=$3
if [ "$beam_or_laser" == "beam" ]; then
    option="beam"
elif [ "$beam_or_laser" == "laser" ]; then
    option="laser"
elif [ "$beam_or_laser" == "beam+laser" ]; then
    OPT=$(($SPILL_NO % $SPILL_LASER))
    if [ "$OPT" -eq 0 ]; then
        option="laser"
    else
        option="beam"
    fi
else
    echo "Third argument must be 'beam', 'laser' or 'beam+laser'"
    exit 1
fi
SPILL_TYPE="${SPILL}_${option}"

PLOT_MAIN_FOLDER="/eos/user/m/mcampana/www/h4dqm/ECAL_TB_2025"

WORKING_DIR="/afs/cern.ch/user/e/ecalgit/ECAL_TB2025_laser_preTB"

# --- Start global timer ---
start_time=$(date +%s)

#source /cvmfs/sft.cern.ch/lcg/views/LCG_108/x86_64-el9-gcc13-opt/setup.sh

RECO_UNPACKED_OUTDIR="/eos/cms/store/group/dpg_ecal/comm_ecal/upgrade/testbeam/ECALTB_H4_Oct2025/"
mkdir -p ${RECO_UNPACKED_OUTDIR}/DataTree/$RUN/
UNPACKED_FILE="${RECO_UNPACKED_OUTDIR}/DataTree/$RUN/${SPILL}.root"

EBETE_DIR="/afs/cern.ch/user/e/ecalgit/EBeTe/"
#EBETE_DIR="/afs/cern.ch/user/e/ecalgit/EBeTe_laser_preTB/"

cd ${EBETE_DIR}

# --- EBeTe compilation ---
echo "Building EBeTe and unpacking run $RUN spill $SPILL..."
#make -j
export LD_LIBRARY_PATH="${EBETE_DIR}/build:$LD_LIBRARY_PATH"
echo "Unpacking run $RUN spill $SPILL with EBeTe..."

RAW_DIR="/eos/cms/store/group/dpg_ecal/comm_ecal/upgrade/testbeam/ECALTB_H4_Oct2025/EB/"
#RAW_DIR="/eos/cms/store/group/dpg_ecal/comm_ecal/upgrade/testbeam/ECALTB_H4_Jul2023/EB"
echo "./h4_raw2root ${RAW_DIR}/$RUN/$SPILL.raw ${UNPACKED_FILE}"
./h4_raw2root ${RAW_DIR}/$RUN/$SPILL.raw ${UNPACKED_FILE}

echo "Unpacked DONE for run $RUN spill $SPILL with EBeTe..."

mkdir -p ${RECO_UNPACKED_OUTDIR}/reco/run_$RUN/
mkdir $PLOT_MAIN_FOLDER/run_$RUN/
PLOT_CURRENT_FOLDER=$PLOT_MAIN_FOLDER/run_$RUN/${option}_current_spill/

mkdir $PLOT_CURRENT_FOLDER

cd $WORKING_DIR

/bin/cp *.php $PLOT_MAIN_FOLDER
/bin/cp *.php $PLOT_MAIN_FOLDER/run_$RUN/
/bin/cp *.php $PLOT_CURRENT_FOLDER

# --- Reco and plotting ---
echo "Starting reconstruction and plotting..."
#source ${HOME}/ferrari_on_cvmfs_108/bin/activate

echo "plotting in: $PLOT_CURRENT_FOLDER"

python3 reco.py -i ${UNPACKED_FILE} \
    -r "$RUN" \
    -s "$SPILL" \
    -ro ${RECO_UNPACKED_OUTDIR}/reco/run_$RUN/ \
    -j detectors_conf.json \
    -p plotlists/plot_list_$option.csv \
    -po $PLOT_CURRENT_FOLDER \
    -hd "source ${WORKING_DIR}/hadd.sh $RUN plotlists/plot_list_$option.csv $SPILL $PLOT_MAIN_FOLDER $option &" \
    -opt $option

end_time=$(date +%s)
total_time=$((end_time - start_time))
echo "Total elapsed time: $total_time seconds."

# --- Saving plot for selected spills ---
if [ "$beam_or_laser" == "beam" ] || [ "$beam_or_laser" == "laser" ]; then
    if [ "$SPILL_NO" -lt "$SPILL_REP" ] || [ $((SPILL_NO % SPILL_REP)) -eq $((SPILL_REP - 1)) ]; then
        echo ">>> Spill $SPILL_TYPE selezionato, salvo anche in $PLOT_MAIN_FOLDER/run_$RUN/spill_$SPILL_TYPE <<<"
        cp -rT "$PLOT_MAIN_FOLDER/run_$RUN/${option}_current_spill" "$PLOT_MAIN_FOLDER/run_$RUN/spill_$SPILL_TYPE"

    fi
else
    if [ "$SPILL_NO" -lt "$SPILL_REP" ] || [ $((SPILL_NO % SPILL_LASER)) -eq 0 ] || [ $((SPILL_NO % SPILL_REP)) -eq $((SPILL_REP - 1)) ]; then
        echo ">>> Spill $SPILL_TYPE selezionato, salvo anche in $PLOT_MAIN_FOLDER/run_$RUN/spill_$SPILL_TYPE <<<"
        cp -rT "$PLOT_MAIN_FOLDER/run_$RUN/${option}_current_spill" "$PLOT_MAIN_FOLDER/run_$RUN/spill_$SPILL_TYPE"

    fi
fi
