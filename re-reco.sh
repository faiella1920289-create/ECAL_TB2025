#/cvmfs/sft.cern.ch/lcg/views/LCG_106/x86_64-el9-gcc13-opt/setup.sh to make the hadd

RUN=$1

RECO_FOLDER="/eos/cms/store/group/dpg_ecal/comm_ecal/upgrade/testbeam/ECALTB_H4_Oct2025/reco/"
LOGS_FOLDER="/eos/cms/store/group/dpg_ecal/comm_ecal/upgrade/testbeam/ECALTB_H4_Oct2025/reco/re-reco-logs/"
DONE_FILE="/tmp/done_files.txt"

mkdir -p $LOGS_FOLDER

for spill_str in $(ls -1 "$RECO_FOLDER/run_$RUN/${RUN}_"*.root | awk -F "_" '{print $(NF-1)}'); do

    # Convert spill number safely (leading zeros → decimal)
    spill=$((10#$spill_str))

    # Skip spills divisible by 3
    if (( spill % 3 == 0 )); then
        echo "Skipping spill $spill (divisible by 3)"
        continue
    fi

    echo $RECO_FOLDER/run_$RUN/${RUN}_$(printf"%04d" $((10#$spill))).root > $DONE_FILE

    echo "Processing spill $spill"

    # Launch background job for this actual spill
    bash -c "./process_run.sh $RUN $spill pions noplots nounpack > $LOGS_FOLDER/log_${RUN}_{$spill}.log 2>&1 &"

    while true; do
        running=$(ps aux | grep "bash -c ./process_run.sh" | grep -v grep | wc -l)
        if (( running < 12 )); then
            break
        fi
        sleep 1
    done

done

echo list of files re-recoed in $DONE_FILE
