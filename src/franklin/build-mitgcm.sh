#!/bin/bash

cwd=$(pwd)
cluster='galapagos'
simulation='uniformshelf'
node='franklin'

################################## DO NOT MODIFY BELOW ####################################
#               (unless you really know what you're doing....)
###########################################################################################

dirModel="${cwd}/MITgcm"
exedir=$cwd/simulations/$simulation/exe/$node

source $cwd/modules/$cluster/$node

echo "----------------------------"
module list
echo "----------------------------"

# COMPILE
mkdir -p $cwd/build

cd $cwd/build/
rm -rf ./*
$dirModel/tools/genmake2 -rootdir=$dirModel -mods=$cwd/simulations/$simulation/code -ds -mpi -optfile $cwd/opt/$cluster
make depend
make -j 2
cd ../

# Copy executable to exe directory
mkdir -p $exedir
cp -p ./build/mitgcmuv $exedir/mitgcmuv
cp -p ./build/Makefile $exedir/Makefile