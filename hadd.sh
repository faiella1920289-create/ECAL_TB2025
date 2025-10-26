PLOT_LIST=$1 #abs path
MAIN_FOLDER=$2

option="beam"

MAX_JOBS=12

HADD_NOW_DIRS="$MAIN_FOLDER/to_hadd_now.txt"
HADD_GLOB_BUFFER="$MAIN_FOLDER/to_hadd_buffer.txt"

RUN_NO=$(cat ${HADD_NOW_DIRS} | tail -n 1 | awk -F "run_" '{print $2}' | awk -F "/" '{print $1}')

echo $RUN_NO

mkdir ${MAIN_FOLDER}/run_${RUN_NO}/${option}_all_spill/

echo "hadding (output in /dev/null - to debug open the code...)"

#/bin/cp ${MAIN_FOLDER}/*.php ${MAIN_FOLDER}/run_${RUN_NO}/${option}_all_spill/
/bin/cp/*.php ${MAIN_FOLDER}/run_${RUN_NO}/${option}_all_spill/

tail -n +2 $PLOT_LIST | grep -v '#' | while read plot || [[ -n $plot ]]; do
  #echo $plot
  name=$(echo $plot | awk -F "," '{print $1}')
  subfolder=$(echo $plot | awk -F "," '{print $3}')

  #echo $name $subfolder

  mkdir ${MAIN_FOLDER}/run_${RUN_NO}/${option}_all_spill/$subfolder

  FILES=$(cat ${HADD_NOW_DIRS} | grep run_${RUN_NO} | awk -v name="$name" -v sf="$subfolder" '{print $1"/"sf"/"name".root"}' | tr '\n' ' ')
  echo $FILES
  dest="${MAIN_FOLDER}/run_${RUN_NO}/${option}_all_spill/$subfolder/$name.root"

  if [ -e "$dest" ]; then
    #echo "File exists"
    hadd_cmd="hadd -a $dest $FILES"

    root -l -b -q "fileCheck.C(\"$dest\", \"$name\")" | grep "FILE_OK"
    if [ $? == 0 ]; then
      echo "$dest contains histogram $name"
    else
      echo "$dest does not contain histogram $name or is zombie"
      hadd_cmd="hadd $dest $FILES"
    fi
  else
    #echo "File does not exist"
    hadd_cmd="hadd -f $dest $FILES"
  fi

  bash -c "$hadd_cmd" > "${MAIN_FOLDER}/run_${RUN_NO}/${option}_all_spill/${subfolder}/${name}.log" 2>&1 &

  # Control max concurrency:
  while true; do
    # Count running hadd processes of this user
    running_jobs=$(pgrep -cf "hadd")

    if [ "$running_jobs" -lt "$MAX_JOBS" ]; then
      break
    fi
    sleep 5
  done

done

diff ${HADD_NOW_DIRS} ${HADD_GLOB_BUFFER} > /dev/null 2>&1
if [ $? -eq 0 ]; then
  rm ${HADD_GLOB_BUFFER}
  rm ${HADD_NOW_DIRS}
else
  #echo "Files differ"
  grep -Fvx -f ${HADD_NOW_DIRS} ${HADD_GLOB_BUFFER} | grep run_${RUN_NO} > ../temp
  rm ${HADD_NOW_DIRS}
  cat ../temp > ${HADD_GLOB_BUFFER}
fi

python3 plot_hadded.py -po ${MAIN_FOLDER}/run_${RUN_NO}/${option}_all_spill/ -pl $PLOT_LIST

#echo "----------------- hadd and plot-hadded done -----------------"
