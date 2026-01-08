import xarray as xr
import numpy as np
import xgcm
from matplotlib import pyplot as plt

output_dir = 'output/plots/eta'
file_name = 'output/state.nc'
# open the data
ds = xr.open_dataset(file_name)
grid = xgcm.Grid(ds)

print(ds)

# Loop over time steps and save movie
for i in range(len(ds['T'])):
    fig, ax = plt.subplots()
    ds['Eta'][i,:,:].plot(ax=ax, vmin=-1.5, vmax=1.5, cmap='RdBu_r')
    time_days = ds['T'][i].values / (24 * 3600)  # Convert seconds to days
    plt.title(f'Time: {time_days:.2f} days')
    # Pad the frame id with leading zeros
    frame_id = str(i).zfill(4)
    plt.savefig(f'{output_dir}/frame_{str(i).zfill(4)}.png')
    plt.close()
# Create a gif from the saved frames
import imageio
import os
# Create a list of image file names
image_files = []
for i in range(len(ds['T'])):
    # Pad the frame id with leading zeros
    frame_id = str(i).zfill(4)
    image_files.append(f'{output_dir}/frame_{frame_id}.png')


# Create a mp4 from the images
import cv2
# Get the dimensions of the first image
img = cv2.imread(image_files[0])
height, width, layers = img.shape
# Define the codec and create VideoWriter object
fourcc = cv2.VideoWriter_fourcc(*'mp4v')
video = cv2.VideoWriter(f'{output_dir}/eta.mp4', fourcc, 10, (width, height))
# Loop through the images and write them to the video
for filename in image_files:
    img = cv2.imread(filename)
    video.write(img)
# Release the video writer
video.release()

# Remove the image files
for filename in image_files:
    os.remove(filename)