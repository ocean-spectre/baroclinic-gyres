import xarray as xr
import numpy as np
import xgcm
from matplotlib import pyplot as plt
import os
import glob
import cv2

cluster=os.getenv('cluster', 'galapagos')
simulation=os.getenv('simulation', 'uniformshelf_DRAKKAR_25')
cwd=os.getenv('cwd', os.getcwd())
outdir=os.getenv('outdir', f'{cwd}/simulations/{simulation}/output/full_output')

file_name = f'{outdir}/state_*.nc'

km_to_m = 1e3
m_to_km = 1e-3

type = 'meridional_velocity' #MAKE PLOT TYPE EITHER 'temperature' or 'meridional_velocity'

output_dir = f'{outdir}/plots/xsection/{type}'

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

# construct indices for y crosss sections of interest
index_y_1000 = np.abs(ds['Yp1'] - 1000*km_to_m).argmin().values
index_y_1500 = np.abs(ds['Yp1'] - 1500*km_to_m).argmin().values
index_y_2000 = np.abs(ds['Yp1'] - 2000*km_to_m).argmin().values
index_y_2500 = np.abs(ds['Yp1'] - 2500*km_to_m).argmin().values

y_locations = [index_y_1000, index_y_1500, index_y_2000, index_y_2500]
# Loop over time steps and save movie
for i in range(len(ds['T'])):
    fig, axs = plt.subplots(2, 2, figsize=(10,8))
    
    # plot each cross section
    for ax, loc in zip(axs.flatten(), y_locations):
        if type == 'temperature':
            ds['Temp'][i, :, loc, :].plot(ax=ax, cmap='RdBu_r', vmin=2.5, vmax=25)
            ds['Temp'][i,:, loc,:].plot.contour(ax=ax, colors='k', levels=[0, 3, 6, 9, 12, 14, 16, 18, 20, 22, 24, 26], linestyles='--', linewidths=1, vmin=3, vmax=25)
        elif type == 'meridional_velocity':
            ds['V'][i, :, loc, :].plot(ax=ax, cmap='RdBu_r', vmin=-0.6, vmax=0.6)
            ds['Temp'][i, :, loc, :-4].plot.contour(ax=ax, colors='k', levels=[0], linewidths=1)
    for ax, loc in zip(axs.flatten(), y_locations):
        ax.set_title(f'Y = {int(ds["Yp1"][loc].values * m_to_km)} km')
        ax.set_xlabel('X (m)')
        ax.set_ylabel('Depth (m)')
        
    time_days = ds['T'][i].values / (24 * 3600)  # Convert seconds to days
    plt.suptitle(f'{type} at Different Y km\nTime: {time_days:.2f} days')
    plt.tight_layout()
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
video = cv2.VideoWriter(f'{output_dir}/xsections_{type}.mp4', fourcc, 10, (width, height))
# Loop through the images and write them to the video
for filename in image_files:
    img = cv2.imread(filename)
    video.write(img)
# Release the video writer
video.release()

# Remove the image files
for filename in image_files:
    os.remove(filename)
