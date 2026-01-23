#!/bin/bash
#SBATCH --job-name=ke_monitor
#SBATCH --time=01:00:00
#SBATCH --output=ke.out
#SBATCH --error=ke.err
#SBATCH --ntasks=24
#SBATCH --cpus-per-task=1
#SBATCH --mem=32G
#SBATCH --nodelist=noether
#SBATCH --exclusive

source /home/wyatt/miniconda3/etc/profile.d/conda.sh

export cwd=$(pwd)
export cluster='galapagos'
export simulation='uniformshelf'
export rundir=$simulation/run/run_6
export outdir=$cwd/simulations/$simulation/output/output_6

cd $cwd/simulations/$rundir

conda activate baroclinic_gyres

# Glue the state files together
# Files are mnc_*/state.{time}.*.nc
for i in $(ls mnc_0001/state.*.nc | awk -F "." '{print $2}'); do
    echo $i
    # Glue the state files together
    ../../../../MITgcm/utils/python/MITgcmutils/scripts/gluemncbig -o $outdir/state_$i.nc mnc_00*/state.$i.*.nc

    # only need state file for ke calculation
    done
# Glue the grid
../../../../MITgcm/utils/python/MITgcmutils/scripts/gluemncbig -o $outdir/grid.nc mnc_00*/grid.*.nc

python $cwd/src/ke_monitor.py

conda deactivate

rm $outdir/*.nc