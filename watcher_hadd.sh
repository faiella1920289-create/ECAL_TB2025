PLOT_LIST=$1 #abs path
MAIN_FOLDER=$2

option="beam"

MAX_JOBS=12

HADD_NOW_DIRS="$MAIN_FOLDER/to_hadd_now.txt"
HADD_GLOB_BUFFER="$MAIN_FOLDER/to_hadd_buffer.txt"

while true; do
  if [ -e ${HADD_NOW_DIRS} ]; then
    echo $HADD_NOW_DIRS exists, starting
    timeout 100s bash hadd.sh $1 $2 > $MAIN_FOLDER/logs/hadd_$(date | sed 's/ /-/g') 2>&1;
  fi
  echo $HADD_NOW_DIRS not found, sleeping 2 seconds and retrying
  echo "for DEBUG, cat of ${HADD_GLOB_BUFFER}"
  cat ${HADD_GLOB_BUFFER}
  sleep 2
done
