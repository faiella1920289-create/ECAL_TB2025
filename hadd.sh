run_no=$1
plot_list=$2 #abs path
n_spill=$3
main_folder=$4
option=$5

echo "conf: $conf"

mkdir ${main_folder}/run_$run_no/${option}_all_spill/

echo "hadding (output in /dev/null - to debug open the code...)"
for folder in $(ls -1d ${main_folder}/run_$run_no/${option}_current_spill/*/); do
  mkdir ${main_folder}/run_$run_no/${option}_all_spill/$(basename $folder)
  for file in $(ls -1 $folder/*.root); do
    source="${main_folder}/run_$run_no/${option}_current_spill/$(basename $folder)/$(basename $file)"
    dest="${main_folder}/run_$run_no/${option}_all_spill/$(basename $folder)/$(basename $file)"

    filename=$(basename $file)
    plot="${filename::-5}"
    echo $plot
    if [[ -n $(cat $plot_list | grep -v '#' | grep $plot) ]]; then
      if [ ! -f $dest ]; then
        cp $source $dest;
      else
        hadd -a $dest $source > /dev/null 2>&1;
      fi
    fi
  done
done

/bin/cp ${main_folder}/*.php ${main_folder}/run_$run_no/${option}_all_spill/

python3 plot_hadded.py -po ${main_folder}/run_$run_no/${option}_all_spill/ -pl $plot_list

echo "----------------- hadd and plot-hadded done -----------------"
