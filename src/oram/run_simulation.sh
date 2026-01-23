#!/bin/bash
#SBATCH --job-name=mitgcmuv
#SBATCH --output=mitgcmuv.out
#SBATCH --error=mitgcmuv.err
#SBATCH --time=56:00:00
#SBATCH --ntasks=24
#SBATCH --cpus-per-task=1
#SBATCH --mem=32G
#SBATCH --nodelist=oram
#SBATCH --exclusive

source /home/wyatt/miniconda3/etc/profile.d/conda.sh

export cwd=$(pwd)
export cluster='galapagos'
export node='oram'
export simulation='uniformshelf'
export rundir=$simulation/run/run_8
export outdir=$cwd/simulations/$simulation/output/output_8
################################## DO NOT MODIFY BELOW ####################################
#               (unless you really know what you're doing....)
###########################################################################################

python $cwd/src/log_time.py

dirModel="${cwd}/MITgcm"
exedir=$cwd/simulations/$simulation/exe/$node

source $cwd/modules/$cluster/$node

echo "----------------------------"
module list
echo "----------------------------"

cd $cwd/simulations/$rundir
mpirun --use-hwthread-cpus -np $SLURM_NTASKS $exedir/mitgcmuv

mkdir -p $outdir

python $cwd/src/log_time.py

conda activate baroclinic_gyres

# Glue the state files together
# Files are mnc_*/state.{time}.*.nc
for i in $(ls mnc_0001/state.*.nc | awk -F "." '{print $2}'); do
    echo $i
    # Glue the state files together
    ../../../../MITgcm/utils/python/MITgcmutils/scripts/gluemncbig -o $outdir/state_$i.nc mnc_00*/state.$i.*.nc
    # Glue the diagnostics
    ../../../../MITgcm/utils/python/MITgcmutils/scripts/gluemncbig -o $outdir/dynDiag_$i.nc mnc_00*/dynDiag.$i.*.nc
    ../../../../MITgcm/utils/python/MITgcmutils/scripts/gluemncbig -o $outdir/surfDiag_$i.nc mnc_00*/surfDiag.$i.*.nc
done
# Glue the grid
../../../../MITgcm/utils/python/MITgcmutils/scripts/gluemncbig -o $outdir/grid.nc mnc_00*/grid.*.nc

# Clear the mnc directories
rm -rf mnc_00*

python $cwd/src/log_size.py

# Save pickup files
mkdir -p $outdir/pickup
mv pickup*.meta $outdir/pickup/
mv pickup*.data $outdir/pickup/

# Save stdout files
mkdir $outdir/stdouterr
mv STDOUT.* $outdir/stdouterr/
mv STDERR.* $outdir/stdouterr/

# Save mitgcm.out and mitgcm.err files
mv $cwd/mitgcm.* $outdir

# Create animation of the free surface height
python $cwd/src/animate_eta.py
python $cwd/src/ke_timeseries.py
python $cwd/src/animate_sst.py
#python $cwd/src/animate_barotropic_vorticity.py
#python $cwd/src/animate_barotropic_streamfunction.py

