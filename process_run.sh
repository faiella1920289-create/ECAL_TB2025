cd /afs/cern.ch/user/e/ecalgit/ECAL_TB2025_laser_preTB

timeout 120s ./fullexecution.sh "$@" 2>&1 | tee /eos/user/m/mcampana/www/h4dqm/ECAL_TB_2025/logs/log_run${1}_spill${2}_typeis${3}.log
