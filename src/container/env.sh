#!/bin/bash

# Path where downloaded data is stored
SIMULATION="testing_container"
export MITGCM_BASE_IMG="docker://ghcr.io#fluidnumerics/mitgcm-containers/gcc-openmpi:latest"
export SIMULATION_DIR=/home/wyatt/beegfs/baroclinic-gyres/simulations/$SIMULATION