import xarray as xr
import matplotlib.pyplot as plt
import xgcm
import os
import glob
import numpy as np
import warnings

# ADJUST TIMESTEP HERE
timestep = 600 # seconds

simulation=os.getenv('simulation', 'uniformshelf_DRAKKAR_25')
cwd = os.getcwd()

outdir=os.getenv('OUT_PATH', f'{cwd}/simulations/{simulation}/output/full_output')

output_dir = f'{outdir}/plots/cfl'
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

# open the dataset with chunks to avoid loading everything into memory
ds = xr.open_mfdataset(file_list, chunks={'T': 1})

# create horizontal grid for ke interpolation
coords = {
    "X": {"center": "X", "left": "Xp1"},
    "Y": {"center": "Y", "left": "Yp1"},
    "Z": {"center": "Z", "outer": "Zl"},
}

grid = xgcm.Grid(ds, coords=coords, periodic=False, autoparse_metadata=False)

# Get grid spacings
delR = (ds.Zl[1:].values - ds.Zl[:-1].values)
diff_last = 2*(ds.Zl[len(delR)].values - ds.Z[len(delR)].values)
delR = np.abs(np.append(delR, diff_last))

dx = (ds.Xp1.values[1:] - ds.Xp1.values[:-1])
dy = (ds.Yp1.values[1:] - ds.Yp1.values[:-1])

# Process all timesteps at once using vectorized operations
# trim u and v to same shape
# since Xp1/Yp1 grids have an extra point due to staggering, xarray gets upset when trying to load data even after interpolation
# I believe this is okay since wall data has 0 velocity. -WS
u = ds['U'][:, :, :, :-1]
v = ds['V'][:, :, :-1, :]
w = ds['W']

# suppress overflow warnings from xgcm interpolation, handled during xarray calculation
with warnings.catch_warnings():
    warnings.filterwarnings('ignore', category=RuntimeWarning, message='overflow encountered')
    warnings.filterwarnings('ignore', category=RuntimeWarning, message='invalid value encountered')
    warnings.filterwarnings('ignore', category=RuntimeWarning, message='All-NaN slice encountered')
    
    # interpolate onto cell centers (lazy operations with dask)
    u_centered = grid.interp(u, 'X')
    v_centered = grid.interp(v, 'Y')

    # compute cfl for all timesteps at once using xarray operations, avoiding NaN values
    cfl_x = (np.abs(u_centered) * timestep / xr.DataArray(dx, dims='X')).max(dim=["Z", "Y", "X"]).values
    cfl_y = (np.abs(v_centered) * timestep / xr.DataArray(dy, dims='Y')).max(dim=["Z", "Y", "X"]).values
    cfl_z = (np.abs(w) * timestep / np.abs(xr.DataArray(delR, dims='Zl'))).max(dim=["Zl", "Y", "X"]).values
    #print(np.abs(w).max(dim=["Zl", "Y", "X"]).values)
    
#print(f"CFL_x: {cfl_x}")
#print(f"CFL_y: {cfl_y}")
#print(f"CFL_z: {cfl_z}")

#print("dx:", dx)
#print("dy:", dy)

# Plot timerseries for the max cfl across dimensions
time = ds['T'].values / (3600*24) # Convert seconds to days
plt.plot(time, cfl_x, label='CFL_x')
plt.plot(time, cfl_y, label='CFL_y')
plt.plot(time, cfl_z, label='CFL_z')
plt.ylim([1e-5, 1.5e0])
plt.yscale('log')
plt.xlabel('Time (s)')
plt.ylabel(r'CFL [$U \Delta t / \Delta x$]')
plt.legend()
plt.title('CFL Timeseries for each Velocity Component')
plt.savefig(f'{output_dir}/cfl_numbers.png', dpi=300)