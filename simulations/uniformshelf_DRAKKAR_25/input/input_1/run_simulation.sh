#!/bin/bash
#SBATCH --job-name=mitgcmuv
#SBATCH --output=mitgcmuv.out
#SBATCH --error=mitgcmuv.err
#SBATCH --time=12:00:00
#SBATCH --ntasks=24
#SBATCH --cpus-per-task=1
#SBATCH --mem=32G
#SBATCH --nodelist=oram

export OUTDIR="./output"
module purge
module load gcc/12.4.0
module load openmpi/5.0.6
module load netcdf-c/4.9.2
module load netcdf-fortran/4.6.1
export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:$NETCDF_FORTRAN_ROOT/lib
export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:$NETCDF_C_ROOT/lib
source "/home/joe/miniconda3/etc/profile.d/conda.sh"

mpirun -np 24 ./mitgcmuv

#TODO : Post-processing to call gluemmncbig
mkdir -p $OUTDIR
# Glue the state files together
# TODO : Find the individual time levels from the filenames and glue per time level
# Files are mnc_*/state.{time}.*.nc
for i in $(ls mnc_0001/state.*.nc | awk -F "." '{print $2}'); do
    echo $i
    # Glue the state files together
    ../../../utils/python/MITgcmutils/scripts/gluemncbig -o $OUTDIR/state_$i.nc mnc_00*/state.$i.*.nc
    # Glue the diagnostics
    ../../../utils/python/MITgcmutils/scripts/gluemncbig -o $OUTDIR/dynDiag_$i.nc mnc_00*/dynDiag.$i.*.nc
    ../../../utils/python/MITgcmutils/scripts/gluemncbig -o $OUTDIR/surfDiag_$i.nc mnc_00*/surfDiag.$i.*.nc
done
# Glue the grid
../../../utils/python/MITgcmutils/scripts/gluemncbig -o $OUTDIR/grid.nc mnc_00*/grid.*.nc


# Move the pickup files to a separate directory
mkdir -p ${OUTDIR}/pickup
mv pickup*.meta ${OUTDIR}/pickup/
mv pickup*.data ${OUTDIR}/pickup/

# Save stdout files
mkdir ${OUTDIR}/stdouterr
mv STDOUT.* ${OUTDIR}/stdouterr/
mv STDERR.* ${OUTDIR}/stdouterr/

# Clear the mnc directories
rm -rf mnc_00*

# Create animation of the free surface height
mkdir -p $OUTDIR/plots/eta
conda activate xgcm
python ./plot_results.py
