#!/bin/bash
#SBATCH -n64
#SBATCH -c1
#SBATCH --job-name=baroclinic-gyres-run
#SBATCH --output=%x-%A.out
#SBATCH --error=%x-%A.out

export cwd=$(pwd)
export RUN_DIR="run/"
export OUT_DIR="output/"
source /home/wyatt/miniconda3/etc/profile.d/conda.sh

if [ -n "${SLURM_JOB_ID:-}" ]; then
    SCRIPT_PATH=$(scontrol show job "$SLURM_JOB_ID" --json | jq -r '.jobs[0].command' )
    SCRIPT_DIR=$(dirname "$(readlink -f "$SCRIPT_PATH")")
    # define SIMULATION_DIR in env.sh for this workflow
    #SIMULATION_DIR=$(dirname $SCRIPT_DIR)
else
    # Fallback for when running the script outside of a Slurm job
    SCRIPT_DIR=$(dirname "$(readlink -f "$0")")
fi

source $SCRIPT_DIR/env.sh
mkdir -p $SIMULATION_DIR/$OUT_DIR
python $cwd/src/log_time.py

echo "======================================="
echo ""
echo " Using simulation directory : ${SIMULATION_DIR}"
echo " Using run directory        : ${RUN_DIR}"
echo " Using MITgcm base image    : ${MITGCM_BASE_IMG}"
echo ""
echo "======================================="

###############################################################################
# Set up run directory
###############################################################################
if [[ ! -d "$RUN_DIR" ]]; then
  echo "-------------------------------------"
  echo "  > Directory $RUN_DIR does not exist. Setting up the run directory now..."
  echo ""
  srun --ntasks=1 \
       --mpi=pmix \
       --container-image=$MITGCM_BASE_IMG \
       --container-mounts=$SIMULATION_DIR:/workspace:rw \
       --container-env=RUN_DIR \
       /bin/bash -c /workspace/workflows/run_setup.sh
  echo ""
  echo "  > Done setting up the run directory!"
  echo ""
  echo "-------------------------------------"
fi

###############################################################################
# Launch mitgcm under enroot container
###############################################################################
srun --mpi=pmix \
     --container-image=$MITGCM_BASE_IMG \
     --container-mounts=$SIMULATION_DIR:/workspace:rw \
     --container-env=RUN_DIR \
     /bin/bash -c /workspace/workflows/run_worker.sh

mv $cwd/*$SLURM_JOB_ID.out $SIMULATION_DIR/$RUN_DIR

################################################################################
# Glue files together and move to output directory
################################################################################
python $cwd/src/log_time.py

conda activate baroclinic_gyres

GLUEMNC_PATH=$cwd/MITgcm/utils/python/MITgcmutils/scripts/gluemncbig
RUN_PATH=$SIMULATION_DIR/$RUN_DIR
export OUT_PATH=$SIMULATION_DIR/$OUT_DIR

cd $RUN_PATH

# Glue the state files together
# Files are mnc_*/state.{time}.*.nc
for i in $(ls mnc_0001/state.*.nc | awk -F "." '{print $2}'); do
    $GLUEMNC_PATH -o $OUT_PATH/state_$i.nc mnc_00*/state.$i.*.nc
    $GLUEMNC_PATH -o $OUT_PATH/dynDiag_$i.nc mnc_00*/dynDiag.$i.*.nc
    $GLUEMNC_PATH -o $OUT_PATH/surfDiag_$i.nc mnc_00*/surfDiag.$i.*.nc
done
# Glue the grid
$GLUEMNC_PATH -o $OUT_PATH/grid.nc mnc_00*/grid.*.nc

# Clear the mnc directories
rm -rf mnc_00*

# Save pickup files
mkdir -p $OUT_PATH/pickup
mv pickup*.meta $OUT_PATH/pickup/
mv pickup*.data $OUT_PATH/pickup/

# Save stdout files
mkdir -p $OUT_PATH/stdouterr
mv STDOUT.* $OUT_PATH/stdouterr/
mv STDERR.* $OUT_PATH/stdouterr/

# Save mitgcm.out and mitgcm.err files
mv $cwd/mitgcmuv.* $OUT_PATH

# Create post processing figures
#python $cwd/src/animate_eta.py
python $cwd/src/ke_timeseries.py
python $cwd/src/animate_sst.py
python $cwd/src/cfl.py
#python $cwd/src/animate_cross_section.py