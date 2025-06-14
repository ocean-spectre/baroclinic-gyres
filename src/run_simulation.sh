#!/bin/bash
#SBATCH --job-name=mitgcmuv
#SBATCH --output=mitgcmuv.out
#SBATCH --error=mitgcmuv.err
#SBATCH --time=12:00:00
#SBATCH --ntasks=24
#SBATCH --cpus-per-task=1
#SBATCH --mem=32G
#SBATCH --nodelist=oram

export cwd=$(pwd)
export cluster='galapagos'
export simulation='uniformshelf'
export outdir=$cwd/simulations/$simulation/output
################################## DO NOT MODIFY BELOW ####################################
#               (unless you really know what you're doing....)
###########################################################################################

dirModel="${cwd}/MITgcm"
exedir=$cwd/simulations/$simulation/exe

source $cwd/modules/$cluster

echo "----------------------------"
module list
echo "----------------------------"

cd $cwd/simulations/$simulation
mpirun -np $SLURM_NTASKS $exedir/mitgcmuv

mkdir -p $outdir
# Glue the state files together
# Files are mnc_*/state.{time}.*.nc
for i in $(ls mnc_0001/state.*.nc | awk -F "." '{print $2}'); do
    echo $i
    # Glue the state files together
    ../../../utils/python/MITgcmutils/scripts/gluemncbig -o $outdir/state_$i.nc mnc_00*/state.$i.*.nc
    # Glue the diagnostics
    ../../../utils/python/MITgcmutils/scripts/gluemncbig -o $outdir/dynDiag_$i.nc mnc_00*/dynDiag.$i.*.nc
    ../../../utils/python/MITgcmutils/scripts/gluemncbig -o $outdir/surfDiag_$i.nc mnc_00*/surfDiag.$i.*.nc
done
# Glue the grid
../../../utils/python/MITgcmutils/scripts/gluemncbig -o $outdir/grid.nc mnc_00*/grid.*.nc

# Clear the mnc directories
rm -rf mnc_00*

# Create animation of the free surface height
conda activate baroclinic_gyres
python $(cwd)/src/plot_results.py
