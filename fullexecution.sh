#!/bin/bash

# --- launch settings with beam|laser as input parameter ---
if [ "$#" -lt 3 ]; then
    echo "Usage: $0 <run_number> <spill_number> <beam|laser|beam+laser> [noplots] [nounpack]"
    exit 1
fi
RUN=$1
SPILL=$(printf "%04d" $((10#$2)))
SPILL_NO=$((10#$SPILL))
SPILL_LASER=3
SPILL_REP=5
mode=$3

if [ "$4" == "noplots" ]; then
  doplots="0"
else
  doplots="1"
fi

nounpack=$5

if [ "$mode" == "laser" ]; then
    option="laser"
elif [[ "$mode" == *"+laser" ]]; then
    # extract the part before +laser
    other="${mode%%+laser}"
    OPT=$(($SPILL_NO % $SPILL_LASER))
    if [ "$OPT" -eq 0 ]; then
        option="laser"
    else
        option="$other"
    fi
else
    option=$mode
fi

echo "spill type is: " $option


SPILL_TYPE="${SPILL}_${option}"

PLOT_MAIN_FOLDER="/eos/user/m/mcampana/www/h4dqm/ECAL_TB_2025"

WORKING_DIR="/afs/cern.ch/user/e/ecalgit/ECAL_TB2025_laser_preTB"

# --- Start global timer ---
start_time=$(date +%s)

#source /cvmfs/sft.cern.ch/lcg/views/LCG_108/x86_64-el9-gcc13-opt/setup.sh

RECO_UNPACKED_OUTDIR="/eos/cms/store/group/dpg_ecal/comm_ecal/upgrade/testbeam/ECALTB_H4_Oct2025/"
UNPACKED_FILE="${RECO_UNPACKED_OUTDIR}/DataTree/$RUN/${SPILL}.root"

if [ "$nounpack" != "nounpack" ]; then
  mkdir -p ${RECO_UNPACKED_OUTDIR}/DataTree/$RUN/
  EBETE_DIR="/afs/cern.ch/user/e/ecalgit/EBeTe/"

  cd ${EBETE_DIR}

  # --- EBeTe compilation ---
  echo "Building EBeTe and unpacking run $RUN spill $SPILL..."
  #make -j
  export LD_LIBRARY_PATH="${EBETE_DIR}/build:$LD_LIBRARY_PATH"
  echo "Unpacking run $RUN spill $SPILL with EBeTe..."

  RAW_DIR="/eos/cms/store/group/dpg_ecal/comm_ecal/upgrade/testbeam/ECALTB_H4_Oct2025/EB/"
  #RAW_DIR="/eos/cms/store/group/dpg_ecal/comm_ecal/upgrade/testbeam/ECALTB_H4_Jul2023/EB"
  echo "./h4_raw2root ${RAW_DIR}/$RUN/$SPILL.raw ${UNPACKED_FILE}"
  ./h4_raw2root ${RAW_DIR}/$RUN/$SPILL.raw ${UNPACKED_FILE} > ${RECO_UNPACKED_OUTDIR}/DataTree/$RUN/${SPILL}.txt

  echo "Unpacked DONE for run $RUN spill $SPILL with EBeTe..."
fi

cd $WORKING_DIR
mkdir -p ${RECO_UNPACKED_OUTDIR}/reco/run_$RUN/

if [ "$doplots" == "1" ]; then
  mkdir $PLOT_MAIN_FOLDER/run_$RUN/
  PLOT_CURRENT_FOLDER=$PLOT_MAIN_FOLDER/run_$RUN/spill_$SPILL_TYPE/

  mkdir $PLOT_CURRENT_FOLDER

  #/bin/cp *.php $PLOT_MAIN_FOLDER
  /bin/cp *.php $PLOT_MAIN_FOLDER/run_$RUN/
  /bin/cp *.php $PLOT_CURRENT_FOLDER
  echo "plotting in: $PLOT_CURRENT_FOLDER"

  plots_options="-p plotlists/plot_list_$option.csv -po $PLOT_CURRENT_FOLDER"
else
  plots_options=""
fi

# --- Reco and plotting ---
echo "Starting reconstruction..."
#source ${HOME}/ferrari_on_cvmfs_108/bin/activate

python3 reco.py -i ${UNPACKED_FILE} \
    -r "$RUN" \
    -s "$SPILL" \
    -ro ${RECO_UNPACKED_OUTDIR}/reco/run_$RUN/ \
    -j detectors_conf.json \
    -hd "source ${WORKING_DIR}/hadd.sh $RUN plotlists/plot_list_$option.csv $SPILL $PLOT_MAIN_FOLDER $option &" \
    -opt $option \
    --do-plots $doplots $plots_options

end_time=$(date +%s)
total_time=$((end_time - start_time))
echo "Total elapsed time: $total_time seconds."

if [ "$doplots" == "1" ]; then
  cp -rT "$PLOT_MAIN_FOLDER/run_$RUN/spill_$SPILL_TYPE" "$PLOT_MAIN_FOLDER/run_$RUN/${option}_current_spill"

  echo $option
  if [ "$option" == "beam" ]; then
    echo "writing folder path to hadd buffer"
    echo $PLOT_MAIN_FOLDER/run_$RUN/spill_$SPILL_TYPE >> $PLOT_MAIN_FOLDER/to_hadd_buffer.txt
  fi

  if [ "$option" == "beam" ] && [ $((SPILL_NO % SPILL_REP)) -eq $((SPILL_REP - 1)) ]; then
    cp $PLOT_MAIN_FOLDER/to_hadd_buffer.txt $PLOT_MAIN_FOLDER/to_hadd_now.txt
  fi
fi
