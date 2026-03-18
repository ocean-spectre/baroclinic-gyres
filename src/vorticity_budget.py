import xarray as xr
import numpy as np
import xgcm
from matplotlib import pyplot as plt
import os
import glob
from dask.distributed import Client

cluster = os.getenv('cluster', 'galapagos')
simulation = os.getenv('simulation', 'uniformshelf_DRAKKAR_25')
cwd = os.getcwd()

outdir = os.getenv('outdir', f'{cwd}/simulations/{simulation}/output/full_output')
wind_file = f'{cwd}/simulations/{simulation}/input/input_1/windx_cosy.bin'

output_dir = f'{outdir}/plots/vorticity_budget'
dyn_file_name = f'{outdir}/dynDiag_*.nc'
grid_file = f'{outdir}/grid.nc'

if not os.path.exists(output_dir):
    os.makedirs(output_dir)

# Get file lists
dyn_files = sorted(glob.glob(dyn_file_name))
if not dyn_files:
    raise FileNotFoundError(f"No files found matching {dyn_file_name}")

# Open datasets
ds_dyn = xr.open_mfdataset(dyn_files, chunks={'T': 1}, data_vars='minimal', compat='override', coords='minimal')
grid_ds = xr.open_dataset(grid_file)

# Trim extra staggered grid points (walls with zero velocity)
ds_dyn = ds_dyn.isel(Xp1=slice(0, -1), Yp1=slice(0, -1))

# xgcm grid
coords_dict = {
    "X": {"center": "X", "left": "Xp1"},
    "Y": {"center": "Y", "left": "Yp1"},
}
xgrid = xgcm.Grid(ds_dyn, coords=coords_dict, periodic=False, autoparse_metadata=False)

# Grid parameters
dx = float(grid_ds.X[1] - grid_ds.X[0])
dy = float(grid_ds.Y[1] - grid_ds.Y[0])
rA = grid_ds.rAc.values          # cell area at centers (Y, X)
rAz = grid_ds.rAz.values         # cell area at vorticity points
hfac = grid_ds.hFacC.values      # (Z, Y, X)
depth = grid_ds.Depth.values     # (Y, X), positive
drF = grid_ds.drF.values         # (Z,)
Z_centers = grid_ds.Z.values     # cell center depths (negative, m)
nz, ny, nx = hfac.shape

# Precompute staggered hFac arrays
hFacW_trim = grid_ds.hFacW.isel(Xp1=slice(0, -1)).values
hFacS_trim = grid_ds.hFacS.isel(Yp1=slice(0, -1)).values
thickness_W = hFacW_trim * drF[:, None, None]
thickness_S = hFacS_trim * drF[:, None, None]
thickness_C = hfac * drF[:, None, None]

# Coordinate arrays for xr.DataArray construction
Y_coord = ds_dyn.Y
Yp1_coord = ds_dyn.Yp1
X_coord = ds_dyn.X
Xp1_coord = ds_dyn.Xp1

# Physical parameters
rho0 = 1000.0   # kg/m^3
Ah = 2.0e2      # m^2/s, horizontal viscosity
f0 = 1.0e-4     # s^-1, Coriolis parameter
beta = 1.0e-11  # 1/(m*s), meridional gradient of f

# Precompute f on staggered grids
f_at_u = f0 + beta * ds_dyn.Y.values[:, None]
f_at_v = f0 + beta * ds_dyn.Yp1.values[:, None]

# Precompute BPT arrays
bottom_k = np.full((ny, nx), -1)
for k in range(nz):
    mask = hfac[k, :, :] > 0
    bottom_k[mask] = k
    
ocean_mask = bottom_k >= 0
jj = np.arange(ny)[:, None]  # (ny, 1) row indices
ii = np.arange(nx)[None, :]  # (1, nx) column indices

# Compute depth gradients on interior ocean cells only (exclude walls)
dHdx = np.zeros((ny, nx))
dHdy = np.zeros((ny, nx))
dHdx[1:-1, 1:-1] = np.gradient(depth[1:-1, 1:-1], dx, axis=1)
dHdy[1:-1, 1:-1] = np.gradient(depth[1:-1, 1:-1], dy, axis=0)

# Interior shape for cell-center interpolations (nonlinear torque)
ny_c = ny - 1
nx_c = nx - 1
rA_c = rA[:ny_c, :nx_c]

phihyd = ds_dyn['PHIHYD']

# ============================================================
# Region definitions
# ============================================================
# Each region defines (y_slice, x_slice) for center-grid and cell-center-grid fields.
# Functions return full 2D fields; integration is done per-region.
mid_y = ny // 2

regions = {
    'southern_gyre': {
        'center': (slice(0, mid_y), slice(None)),
        'cell_center': (slice(0, min(mid_y, ny_c)), slice(None)),
        'title': 'Southern Gyre',
    },
    'northern_gyre': {
        'center': (slice(mid_y, ny), slice(None)),
        'cell_center': (slice(min(mid_y, ny_c), ny_c), slice(None)),
        'title': 'Northern Gyre',
    },
    'full_domain': {
        'center': (slice(0, ny), slice(None)),
        'cell_center': (slice(0, ny_c), slice(None)),
        'title': 'Full Domain',
    },
}

# ============================================================
# Budget term functions — return full 2D fields
# ============================================================
# Budget: dζ̄/dt = J(Pb,h)/ρ0 + A - ∇·(fŪ) + ∇×τw/ρ0 - ∇×τb/ρ0 + Ah∇²ζ̄
#   Term 1: Bottom pressure torque  J(Pb,h)/ρ0
#   Term 2: Nonlinear torque A      (Eq. 2.6)
#   Term 3: Planetary vorticity     -∇·(fŪ)
#   Term 4: Wind stress curl        ∇×τw/ρ0  (constant)
#   Term 5: Bottom drag curl        zero (free-slip bottom, no drag coefficient)
#   Term 6: Viscous torque          Ah∇²ζ̄

def compute_transport(u_vals, v_vals):
    """Depth-integrated transport U (Y, Xp1), V (Yp1, X)."""
    U = (u_vals * thickness_W).sum(axis=0)
    V = (v_vals * thickness_S).sum(axis=0)
    return U, V

def compute_barotropic_vorticity(U, V):
    """Barotropic vorticity ζ̄ = ∂V/∂x - ∂U/∂y at vorticity points."""
    U_da = xr.DataArray(U, dims=('Y', 'Xp1'), coords={'Y': Y_coord, 'Xp1': Xp1_coord})
    V_da = xr.DataArray(V, dims=('Yp1', 'X'), coords={'Yp1': Yp1_coord, 'X': X_coord})
    return (xgrid.diff(V_da, "X") / dx - xgrid.diff(U_da, "Y") / dy).values

def compute_bpt_field(phi):
    """Term 1: Bottom pressure torque J(Pb,h)/rho0 — 2D field on center grid.
    Gradients computed on interior ocean cells only (walls excluded)."""
    phi_bottom = phi[bottom_k, jj, ii]
    phi_bottom[~ocean_mask] = 0.0
    P_b = rho0 * phi_bottom

    # Compute pressure gradients on interior only (skip wall rows/columns)
    dPdx = np.zeros((ny, nx))
    dPdy = np.zeros((ny, nx))
    dPdx[1:-1, 1:-1] = np.gradient(P_b[1:-1, 1:-1], dx, axis=1)
    dPdy[1:-1, 1:-1] = np.gradient(P_b[1:-1, 1:-1], dy, axis=0)

    bpt = (dPdx * dHdy - dPdy * dHdx) / rho0
    return bpt

def compute_nonlinear_field(u_3d, v_3d, w_3d):
    """Term 2: Nonlinear torque — 2D field on cell-center grid (ny_c, nx_c).

    Flux-form: -curl of depth-integrated momentum flux divergence,
    plus boundary terms from the depth integration:
      - Nonlinear vortex tube stretching:  [w * zeta]_{z=-h}^{z=0}
      - Transfer of vertical shear to BT vorticity:
            [dw/dx * v - dw/dy * u]_{z=-h}^{z=0}

    Computes div(uu), div(uv) matching MITgcm's flux-form discretization.
      x-mom flux div: d(uu)/dx + d(vu)/dy + d(wu)/dz
      y-mom flux div: d(uv)/dx + d(vv)/dy + d(wv)/dz
    """
    # ----------------------------------------------------------------
    # Curl of depth-integrated flux divergence
    # ----------------------------------------------------------------
    
    # Interpolate u, v to cell centers for flux products
    u_c = 0.5 * (u_3d[:, :ny_c, :nx_c] + u_3d[:, :ny_c, 1:nx_c+1])
    v_c = 0.5 * (v_3d[:, :ny_c, :nx_c] + v_3d[:, 1:ny_c+1, :nx_c])
    w_c = w_3d[:, :ny_c, :nx_c]

    # Vertical velocity at cell centers (w is at cell top faces)
    w_mid = np.zeros_like(w_c)
    w_mid[:-1] = 0.5 * (w_c[:-1] + w_c[1:])
    w_mid[-1] = 0.5 * w_c[-1]

    # Momentum fluxes (flux form)
    uu = u_c * u_c
    vu = v_c * u_c
    wu = w_mid * u_c
    uv = u_c * v_c
    vv = v_c * v_c
    wv = w_mid * v_c

    # Flux divergence for x-momentum: d(uu)/dx + d(vu)/dy + d(wu)/dz
    flux_div_u = (np.gradient(uu, dx, axis=2)
                  + np.gradient(vu, dy, axis=1)
                  + np.gradient(wu, Z_centers, axis=0))

    # Flux divergence for y-momentum: d(uv)/dx + d(vv)/dy + d(wv)/dz
    flux_div_v = (np.gradient(uv, dx, axis=2)
                  + np.gradient(vv, dy, axis=1)
                  + np.gradient(wv, Z_centers, axis=0))

    # Depth-integrate
    thick_c = thickness_C[:, :ny_c, :nx_c]
    ADV_U = (flux_div_u * thick_c).sum(axis=0)
    ADV_V = (flux_div_v * thick_c).sum(axis=0)

    # Curl of depth-integrated flux divergence: d(ADV_V)/dx - d(ADV_U)/dy
    adv_curl = np.gradient(ADV_V, dx, axis=1) - np.gradient(ADV_U, dy, axis=0)

    # ------------------------------------------------------------------
    # Boundary terms from depth integration of 3D nonlinear vorticity
    # ------------------------------------------------------------------
    bk_c = bottom_k[:ny_c, :nx_c]
    ocean_c = bk_c >= 0
    jj_c = np.arange(ny_c)[:, None]
    ii_c = np.arange(nx_c)[None, :]

    # --- Surface (z=0): WVEL[k=0] is w at the top face (= 0 for rigid lid) ---
    w_surf = w_c[0]
    u_surf = u_c[0]
    v_surf = v_c[0]

    # --- Bottom (z=-h): w at bottom face of deepest cell = WVEL[k+1], or 0 ---
    bk_below = np.minimum(bk_c + 1, nz - 1)
    w_bot = np.where(bk_c + 1 < nz, w_c[bk_below, jj_c, ii_c], 0.0)
    w_bot[~ocean_c] = 0.0
    u_bot = u_c[bk_c, jj_c, ii_c]
    v_bot = v_c[bk_c, jj_c, ii_c]
    u_bot[~ocean_c] = 0.0
    v_bot[~ocean_c] = 0.0

    # Nonlinear vortex tube stretching: [w * zeta]_{z=-h}^{z=0}
    #     zeta = dv/dx - du/dy  (relative vorticity at cell centers)
    zeta_surf = np.gradient(v_surf, dx, axis=1) - np.gradient(u_surf, dy, axis=0)
    zeta_bot = np.gradient(v_bot, dx, axis=1) - np.gradient(u_bot, dy, axis=0)
    vortex_stretch = w_surf * zeta_surf - w_bot * zeta_bot

    # Transfer of vertical shear to BT vorticity:
    #     [dw/dx * v - dw/dy * u]_{z=-h}^{z=0}
    dwdx_surf = np.gradient(w_surf, dx, axis=1)
    dwdy_surf = np.gradient(w_surf, dy, axis=0)
    shear_transfer_surf = dwdx_surf * v_surf - dwdy_surf * u_surf

    dwdx_bot = np.gradient(w_bot, dx, axis=1)
    dwdy_bot = np.gradient(w_bot, dy, axis=0)
    shear_transfer_bot = dwdx_bot * v_bot - dwdy_bot * u_bot
    
    shear_transfer = shear_transfer_surf - shear_transfer_bot

    # Return the sum of the terms
    return adv_curl + vortex_stretch + shear_transfer

def compute_planetary_field(U, V):
    """Term 3: Planetary vorticity -∇·(fŪ) — 2D field on center grid."""
    fU_da = xr.DataArray(f_at_u * U, dims=('Y', 'Xp1'),
                          coords={'Y': Y_coord, 'Xp1': Xp1_coord})
    fV_da = xr.DataArray(f_at_v * V, dims=('Yp1', 'X'),
                          coords={'Yp1': Yp1_coord, 'X': X_coord})
    return -(xgrid.diff(fU_da, "X") / dx + xgrid.diff(fV_da, "Y") / dy).values

def compute_wind_field():
    """Term 4: Wind stress curl ∇xτw/rho0 — 2D field on vorticity grid (constant).
    tau_x lives on U-points (Y, Xp1). Forward difference in y places
    the curl d(tau_x)/dy on vorticity points (Yp1, Xp1)."""
    tau_x = np.fromfile(wind_file, dtype='>f4').reshape((ny, nx))
    return -(tau_x[1:, :] - tau_x[:-1, :]) / (dy * rho0)

def compute_viscous_field(zeta_bt):
    """Term 6: Lateral viscous torque Ah∇²ζ̄ — 2D field on vorticity grid."""
    zeta_padded = np.pad(zeta_bt, 1, mode='constant', constant_values=0)
    d2zdx2 = (zeta_padded[1:-1, 2:] - 2*zeta_padded[1:-1, 1:-1] + zeta_padded[1:-1, :-2]) / dx**2
    d2zdy2 = (zeta_padded[2:, 1:-1] - 2*zeta_padded[1:-1, 1:-1] + zeta_padded[:-2, 1:-1]) / dy**2
    return Ah * (d2zdx2 + d2zdy2)

def integrate_field(field_2d, area, region_slice):
    """Integrate a 2D field over a (y_slice, x_slice) region."""
    ny_f, nx_f = field_2d.shape
    ny_a, nx_a = area.shape
    n = min(ny_f, ny_a)
    m = min(nx_f, nx_a)
    ysl, xsl = region_slice
    return np.nansum(field_2d[:n, :m][ysl, xsl] * area[:n, :m][ysl, xsl])

# ============================================================
# Time setup
# ============================================================
nt = ds_dyn.sizes['T']
time_set = ds_dyn['T'].values
time_days = time_set / (3600 * 24)

# Wind stress curl field (constant in time)
wind_field = compute_wind_field()

# Per-region storage
term_names = ['bpt', 'nonlinear', 'planetary', 'wind', 'viscous', 'tendency', 'zeta_integral']
budget = {}
for region in regions:
    budget[region] = {name: np.zeros(nt) for name in term_names}
    budget[region]['wind'][:] = integrate_field(wind_field, rAz, regions[region]['center'])

# ============================================================
# Main loop
# ============================================================
for i in range(nt):
    u_vals = ds_dyn.UVEL.isel(T=i).values
    v_vals = ds_dyn.VVEL.isel(T=i).values
    w_vals = ds_dyn.WVEL.isel(T=i).values
    phi = phihyd.isel(T=i).values

    U, V = compute_transport(u_vals, v_vals)
    zeta_bt = compute_barotropic_vorticity(U, V)

    # Compute 2D fields (once per timestep)
    bpt_field = compute_bpt_field(phi)
    nl_field = compute_nonlinear_field(u_vals, v_vals, w_vals)
    planet_field = compute_planetary_field(U, V)
    visc_field = compute_viscous_field(zeta_bt)

    # Integrate over each region
    for region, cfg in regions.items():
        budget[region]['zeta_integral'][i] = integrate_field(zeta_bt, rAz, cfg['center'])
        budget[region]['bpt'][i] = integrate_field(bpt_field, rA, cfg['center'])
        budget[region]['nonlinear'][i] = integrate_field(nl_field, rA_c, cfg['cell_center'])
        budget[region]['planetary'][i] = integrate_field(planet_field, rA, cfg['center'])
        budget[region]['viscous'][i] = integrate_field(visc_field, rAz, cfg['center'])

    if (i + 1) % 10 == 0 or i == 0:
        print(f"Timestep {i+1}/{nt}")

# Tendency via centered finite differences
dt = (time_days[1] - time_days[0]) * 3600 * 24
for region in regions:
    z_int = budget[region]['zeta_integral']
    tend = budget[region]['tendency']
    # compute forward/backward difference at first and last timstep
    tend[0] = (z_int[1] - z_int[0]) / dt 
    tend[-1] = (z_int[-1] - z_int[-2]) / dt 
    # centered difference for interior timesteps
    for i in range(1, nt - 1):
        tend[i] = (z_int[i+1] - z_int[i-1]) / (2 * dt)

# Residual: contibution of tendency not calculated within other terms
for region in regions:
    b = budget[region]
    b['residual'] = b['tendency'] - (b['bpt'] + b['nonlinear'] + b['planetary'] + b['wind'] + b['viscous'])

def plot_budget(ax, b, title):
    """Plot all budget terms on an axis."""
    ax.plot(time_days, b['bpt'], 'b-', label='(1) Bottom pressure torque')
    ax.plot(time_days, b['nonlinear'], 'g-', label='(2) Nonlinear torque')
    ax.plot(time_days, b['planetary'], 'c-', label=r'(3) Planetary vorticity $-\nabla \cdot (f\bar{U})$')
    ax.plot(time_days, b['wind'], 'r-', label=r'(4) Wind stress curl', linewidth=2)
    ax.plot(time_days, b['viscous'], 'm-', label=r'(6) Viscous torque ($A_h \nabla^2 \bar{\zeta}$)')
    ax.plot(time_days, b['tendency'], 'k--', label=r'Tendency $\partial \bar{\zeta} / \partial t$', linewidth=1.5)
    ax.plot(time_days, b['residual'], '-', color='gray', label='Residual', linewidth=1.5)
    ax.set_ylabel(r'[m$^3$/s$^2$]')
    ax.set_title(f'Depth-Integrated Vorticity Budget: {title}')
    ax.grid(True, alpha=0.3)
    ax.legend(loc='best', fontsize=7)

# ============================================================
# Plot — Gyre budgets (3 panels, shared axes)
# ============================================================
gyre_regions = ['southern_gyre', 'northern_gyre', 'full_domain']
fig, axes = plt.subplots(3, 1, figsize=(10, 14), sharex=True, sharey=True)

for ax, region in zip(axes, gyre_regions):
    plot_budget(ax, budget[region], regions[region]['title'])

axes[-1].set_xlabel('Time (days)')
plt.tight_layout()
plt.savefig(f'{output_dir}/full_vorticity_budget.png', dpi=300)
plt.close()
