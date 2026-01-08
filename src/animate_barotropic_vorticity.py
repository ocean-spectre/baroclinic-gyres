import xarray as xr
import numpy as np
import xgcm
from matplotlib import pyplot as plt
import os
import glob
import cv2

cluster=os.getenv('cluster', 'galapagos')
simulation=os.getenv('simulation', 'uniformshelf')
cwd = os.getcwd()

# make sure to change simulation number if relying on default instead of environment variable
simulation_number = 1

outdir=os.getenv('outdir', f'{cwd}/simulations/{simulation}/output/output_{simulation_number}')

output_dir = f'{outdir}/plots/barotropic_vorticity'
file_name = f'{outdir}/state_*.nc'
grid_file = f'{outdir}/grid.nc'

# Make the output directory if it does not exist
if not os.path.exists(output_dir):
    os.makedirs(output_dir)
    
# Get the list of files
file_list = glob.glob(file_name)
# Check if the list is empty
if not file_list:
    raise FileNotFoundError(f"No files found matching {file_name}")
# Sort the list of files
file_list.sort()

# open the datasets
ds = xr.open_mfdataset(file_list)
grid_ds = xr.open_dataset(grid_file)

# remove extra Xp1 and Yp1 points so that xarray can load in data without shape mismatches after diff
# I believe this is okay since these points are walls with 0 velocity -WS
ds = ds.isel(Xp1=slice(0, -1), Yp1=slice(0, -1)) 

# create horizontal grid for velocity interpolation
coords = {
    "X": {"center": "X", "left": "Xp1"},
    "Y": {"center": "Y", "left": "Yp1"},
}

grid = xgcm.Grid(ds, coords=coords, periodic=False, autoparse_metadata=False)

vorticity = (grid.diff(ds.V, "X") - grid.diff(ds.U, "Y")) / grid_ds.rAz

barotropic_vorticity = (vorticity * grid_ds.drF).sum('Z')

for i in range(len(ds['T'])):
    fig, ax = plt.subplots()
    h = barotropic_vorticity[i, :, :].plot(ax=ax, vmin=-5e-6, vmax=5e-6, cmap='RdBu_r', add_colorbar=False)
    time_days = ds['T'][i].values / (3600 * 24)
    ax.set_title(f'Time: {time_days:.1f} days')
    fig.colorbar(h, ax=ax, label='Barotropic Vorticity [1/s]')
    plt.savefig(f'{output_dir}/barotropic_vorticity_{str(i).zfill(4)}.png')
    plt.close(fig)
    
# Create a list of image file names
image_files = []
for i in range(len(ds['T'])):
    # Pad the frame id with leading zeros
    frame_id = str(i).zfill(4)
    image_files.append(f'{output_dir}/barotropic_vorticity_{frame_id}.png')
    
# Create a mp4 from the images
# Get the dimensions of the first image
img = cv2.imread(image_files[0])
height, width, layers = img.shape
# Define the codec and create VideoWriter object
fourcc = cv2.VideoWriter_fourcc(*'mp4v')
video = cv2.VideoWriter(f'{output_dir}/barotropic_vorticity.mp4', fourcc, 10, (width, height))
# Loop through the images and write them to the video
for filename in image_files:
    img = cv2.imread(filename)
    video.write(img)
# Release the video writer
video.release()

# Remove the image files
for filename in image_files:
    os.remove(filename)