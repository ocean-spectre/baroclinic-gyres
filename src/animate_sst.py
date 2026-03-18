import xarray as xr
import numpy as np
import xgcm
from matplotlib import pyplot as plt
import os
import glob
import cv2

simulation=os.getenv('simulation', 'uniformshelf_DRAKKAR_25')
cwd=os.getenv('cwd', os.getcwd())
outdir=os.getenv('OUT_PATH', f'{cwd}/simulations/{simulation}/output/full_output')

show_vectors = True   # set True to overlay surface velocity vectors (disables contour)
quiver_stride = 10     # plot every Nth vector in each direction

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

# create horizontal grid for ke interpolation
coords = {
    "X": {"center": "X", "left": "Xp1"},
    "Y": {"center": "Y", "left": "Yp1"},
}

grid = xgcm.Grid(ds, coords=coords, periodic=False, autoparse_metadata=False)


# Precompute surface velocity interpolated to cell centres if needed
if show_vectors:
    u_center = grid.interp(ds['U'][:, 0, :, :], 'X')
    v_center = grid.interp(ds['V'][:, 0, :, :], 'Y')
    s = quiver_stride
    XX, YY = np.meshgrid(ds['X'].values[::s], ds['Y'].values[::s])

# Loop over time steps and save movie
for i in range(len(ds['T'])):
    fig, ax = plt.subplots()
    ds['Temp'][i,0,:,:].plot(ax=ax, cmap='RdBu_r')
    if show_vectors:
        ax.quiver(XX, YY, u_center[i, ::s, ::s].values, v_center[i, ::s, ::s].values)
    else:
        ds['Temp'][i,0,:,:].plot.contour(ax=ax, colors='k', levels=15, linewidths=0.5)
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
video_name = 'sst_vectors.mp4' if show_vectors else 'sst.mp4'
video = cv2.VideoWriter(f'{output_dir}/{video_name}', fourcc, 10, (width, height))
# Loop through the images and write them to the video
for filename in image_files:
    img = cv2.imread(filename)
    video.write(img)
# Release the video writer
video.release()

# Remove the image files
for filename in image_files:
    os.remove(filename)