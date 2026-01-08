import xarray as xr
import matplotlib.pyplot as plt
import xgcm
import os
import glob

cluster=os.getenv('cluster', 'galapagos')
simulation=os.getenv('simulation', 'uniformshelf')
cwd = os.getcwd()

# make sure to change simulation number if relying on default instead of environment variable
simulation_number = 1

outdir=os.getenv('outdir', f'{cwd}/simulations/{simulation}/output/output_{simulation_number}')

output_dir = f'{outdir}/plots/ke'
file_name = f'{outdir}/state_*.nc'

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

# open the dataset
ds = xr.open_mfdataset(file_list)

# create horizontal grid for ke interpolation
coords = {
    "X": {"center": "X", "left": "Xp1"},
    "Y": {"center": "Y", "left": "Yp1"},
}

grid = xgcm.Grid(ds, coords=coords, periodic=False, autoparse_metadata=False)

# interpolate u and v onto the same grid in the center of cells (X, Y)
u = ds['U']
v = ds['V']
# trim u and v to same shape
# since Xp1/Yp1 grids have an extra point due to staggering, xarray gets upset when trying to load data even after interpolation
# I believe this is okay since wall data has 0 velocity. -WS
u = u[:, :, :, :-1]
v = v[:, :, :-1, :]

u_centered = grid.interp(u, 'X')
v_centered = grid.interp(v, 'Y')

# compute kinetic energy and sum
ke = 0.5 * (u_centered**2 + v_centered**2)
total_ke = ke.sum(dim=['X', 'Y', 'Z'])

# plot timeseries
time = ds.T.values/ (24 * 3600) # convert time to days
ke = total_ke.values

plt.plot(time, ke)
plt.xlabel('Time (days)')
plt.ylabel(r'Total Kinetic Energy per unit mass $[\frac{m^2}{s^2}]$')
plt.title('Total KE Timeseries')
plt.grid()
plt.tight_layout()
plt.savefig(f'{output_dir}/ke_timeseries.png')
