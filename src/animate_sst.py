import xarray as xr
import numpy as np
import xgcm
from matplotlib import pyplot as plt
import os
import glob
import cv2

cluster=os.getenv('cluster', 'galapagos')
simulation=os.getenv('simulation', 'uniformshelf')
cwd=os.getenv('cwd', os.getcwd())
outdir=os.getenv('outdir', f'{cwd}/simulations/{simulation}/output/output_4')

output_dir = f'{outdir}/plots/sst'
file_name = f'{outdir}/state_*.nc'

# Make the output directory if it does not exist
if not os.path.exists(output_dir):
    os.makedirs(output_dir)
    
# List of files to be opened
# Use OS to get the list of files

# Get the list of files
file_list = glob.glob(file_name)
# Check if the list is empty
if not file_list:
    raise FileNotFoundError(f"No files found matching {file_name}")
# Sort the list of files
file_list.sort()

# open the data
ds = xr.open_mfdataset(file_list)
grid = xgcm.Grid(ds)

# Loop over time steps and save movie
for i in range(len(ds['T'])):
    fig, ax = plt.subplots()
    ds['Temp'][i,0,:,:].plot(ax=ax, cmap='RdBu_r')
    time_days = ds['T'][i].values / (24 * 3600)  # Convert seconds to days
    plt.title(f'Time: {time_days:.2f} days')
    # Pad the frame id with leading zeros
    frame_id = str(i).zfill(4)
    plt.savefig(f'{output_dir}/frame_{str(i).zfill(4)}.png')
    plt.close()

# Create a list of image file names
image_files = []
for i in range(len(ds['T'])):
    # Pad the frame id with leading zeros
    frame_id = str(i).zfill(4)
    image_files.append(f'{output_dir}/frame_{frame_id}.png')

# Create a mp4 from the images
# Get the dimensions of the first image
img = cv2.imread(image_files[0])
height, width, layers = img.shape
# Define the codec and create VideoWriter object
fourcc = cv2.VideoWriter_fourcc(*'mp4v')
video = cv2.VideoWriter(f'{output_dir}/sst.mp4', fourcc, 10, (width, height))
# Loop through the images and write them to the video
for filename in image_files:
    img = cv2.imread(filename)
    video.write(img)
# Release the video writer
video.release()

# Remove the image files
for filename in image_files:
    os.remove(filename)