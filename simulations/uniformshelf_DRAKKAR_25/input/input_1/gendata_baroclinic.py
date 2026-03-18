import numpy as np
from numpy import cos, pi

Ho = 1800  # depth of ocean (m)
nx = 480    # gridpoints in x
ny = 480    # gridpoints in y
xo = 0     # origin in x,y for ocean domain
yo = 0   # (i.e. southwestern corner of ocean domain)
Lx = 4800 # Length of domain in x (km)
Ly = 4800 # Length of domain in y (km)
#dx = 6400   # grid spacing in x (km)
#dy = 6400   # grid spacing in y (km)
dx = (Lx - xo)/(nx-2)
dy = (Ly - yo)/(ny-2)
hs = 1000 # continental shelf depth (m)
hd = 1800 # open ocean depth (m)
xs = 450 # location of shelf edge (km)
a = 200.0 # length scale for shelf transition width (1/km)
b = 200.0 # length scale for shelf transition width (1/km)

print( f"dx : {dx} (km)" )
print( f"dy : {dy} (km)" )

xeast  = xo + (nx-2)*dx   # eastern extent of ocean domain
ynorth = yo + (ny-2)*dy   # northern extent of ocean domain

xg = np.linspace(xo, xo+Lx, nx+1)
yg = np.linspace(yo, yo+Ly, ny+1)
xc = (xg[:-1] + xg[1:])/2
yc = (yg[:-1] + yg[1:])/2

XC, YC = np.meshgrid(xc, yc, indexing='ij')  # cell centers

# Flat bottom at z=-Ho
h = -Ho * np.ones((ny, nx))

# create a border ring of walls around edge of domain
h[:, [0,-1]] = 0   # set ocean depth to zero at east and west walls
h[[0,-1], :] = 0   # set ocean depth to zero at south and north walls

# Add the continental shelf
h_shelf = hs*np.tanh( XC/a ) + 0.5*(hd-hs)*(np.tanh((XC-xs)/b) + np.tanh(xs/b))
h[1:-1, 1:-1] = -h_shelf[1:-1, 1:-1].transpose() # set ocean depth to shelf depth in interior
# save as single-precision (float32) with big-endian byte ordering
h.astype('>f4').tofile('bathy.bin')

# plot the bathymetry
import matplotlib.pyplot as plt
plt.figure(figsize=(10, 6))
plt.pcolor(XC, YC, h.transpose(), cmap='viridis')
plt.colorbar(label='Depth (m)')
plt.title('Bathymetry of the Ocean Domain')
plt.xlabel('X (km)')
plt.ylabel('Y (km)')
plt.grid()
plt.savefig('bathy.png', dpi=300)

plt.figure(figsize=(10, 6))
plt.plot(xc, h[ny//2, :], label='Bathymetry at centerline')
plt.title('Bathymetry along Centerline')
plt.xlabel('X (km)')
plt.ylabel('Depth (m)')
plt.grid()
plt.savefig('bathy_centerline.png', dpi=300)

# DRAKKAR-75 original vertical cell height taken from ORCA0083-N06 mesh_zgr.nc file
# found at https://gws-access.jasmin.ac.uk/public/nemo/runs/ORCA0083-N06/
DRAKKAR_75_delR = np.array([1.02346105052985, 1.07872551136742, 1.147422971862, 1.23287946082013, 
    1.33912253202836, 1.47091538450047, 1.63370436392059, 1.8334212378883, 
    2.07607544623934, 2.36709064877168, 2.71040469118638, 3.10747300662206, 
    3.55646680517999, 4.05205650736673, 4.58610210403852, 5.14928033447602, 
    5.73327165930689, 6.33285528812769, 6.94731321219471, 7.58088534532088, 
    8.2424120254189, 8.94452744984872, 9.70277448847453, 10.5348834743353, 
    11.4603075349257, 12.4999999859875, 13.6763670550191, 15.0133160058427, 
    16.5363246153755, 18.2724689653435, 20.2503559061838, 22.4999125785179, 
    25.0519889844129, 27.9377329591186, 31.1877026698355, 34.8306927512864, 
    38.89226897249, 43.393034836547, 48.34669227496, 53.7580058379822, 
    59.6208305527706, 65.9164093591275, 72.6121750981931, 79.6612916629742, 
    87.0031286875455, 94.5647802368061, 102.263616852579, 110.01072004038, 
    117.71491571795, 125.287027399477, 132.643933660013, 139.71204661187, 
    146.429920803024, 152.749833059939, 158.638314367781, 164.075737679924, 
    169.055151898934, 173.580594987717, 177.665121537416, 181.328752296138, 
    184.596507880921, 187.496637940804, 190.059109209574, 192.314376396145, 
    194.292430750758, 196.022102183641, 197.530580454257, 198.843117125158, 
    199.982870625355, 200.970860134398, 201.825998730569, 202.565181401784, 
    203.203408497864, 203.753929674028, 204.228397189148])

DRAKKAR_75_Z = np.cumsum(DRAKKAR_75_delR)

# cut of DRAKKAR grid at 25 depth level
DRAKKAR_25_delR = DRAKKAR_75_delR[:25]
DRAKKAR_25_Z = np.cumsum(DRAKKAR_25_delR)

# rescale the 25 depth level DRAKKAR grid to H0
delR = (Ho / DRAKKAR_25_Z[-1]) * DRAKKAR_25_delR
delR.astype('>f4').tofile('dz.bin')

Z = np.cumsum(delR)

print("Total Depth: ", Z[-1], "m")
print("Number of vertical levels: ", len(delR))

# plot the vertical grid
plt.figure()
plt.plot(np.linspace(0, len(delR), len(delR)), -Z)
plt.xlabel('Depth Level (m)')
plt.ylabel('Depth (m)')
plt.title('Vertical Grid')
plt.grid()
plt.savefig('vertical_grid.png', dpi=300)
plt.close()

# plot the vertical grid layers
plt.figure()
plt.plot(np.linspace(0, len(delR), len(delR)), -delR)
plt.xlabel('Depth Level')
plt.ylabel('Layer Thickness (m)')
plt.title('Vertical Grid')
plt.grid()
plt.savefig('vertical_grid_layers.png', dpi=300)
plt.close()

# ocean domain extends from (xo,yo) to (xeast,ynorth)
# (i.e. the ocean spans nx-2, ny-2 grid cells)
# out-of-box-config: xo=0, yo=15, dx=dy=1 deg, ocean extent (0E,15N)-(60E,75N)
# model domain includes a land cell surrounding the ocean domain
# The full model domain cell centers are located at:
#    XC(:,1) = -0.5, +0.5, ..., +60.5 (degrees longitiude)
#    YC(1,:) = 14.5, 15.5, ..., 75.5 (degrees latitude)
# and full model domain cell corners are located at:
#    XG(:,1) = -1,  0, ..., 60 [, 61] (degrees longitiude)
#    YG(1,:) = 14, 15, ..., 75 [, 76] (degrees latitude)
# where the last value in brackets is not included 
# in the MITgcm grid variables XG,YG (but is in variables Xp1,Yp1)
# and reflects the eastern and northern edge of the model domain respectively.
# See section 2.11.4 of the MITgcm users manual.

# Zonal wind-stress
tauMax = 0.1
x = np.linspace(xo-dx, xeast, nx)
y = np.linspace(yo-dy, ynorth, ny) + dy/2
Y, X = np.meshgrid(y, x, indexing='ij')     # zonal wind-stress on (XG,YC) points
tau = -tauMax * cos(2*pi*((Y-yo)/(ny-2)/dy))  # ny-2 accounts for walls at N,S boundaries
tau.astype('>f4').tofile('windx_cosy.bin')

plt.figure(figsize=(10, 6))
plt.pcolor(X, Y, tau, cmap='viridis')
plt.colorbar(label='Wind Stress (N/m^2)')
plt.title('Zonal Wind Stress')
plt.xlabel('Longitude (degrees)')
plt.ylabel('Latitude (degrees)')
plt.grid()
plt.savefig('windx_cosy.png', dpi=300)

# Restoring temperature (function of y only,
# from Tmax at southern edge to Tmin at northern edge)
Tmax = 30
Tmin = 0
Trest = (Tmax-Tmin)/(ny-2)/dy * (ynorth-Y) + Tmin # located and computed at YC points
Trest.astype('>f4').tofile('SST_relax.bin')

plt.figure(figsize=(10, 6))
plt.pcolor(X, Y, Trest, cmap='jet')
plt.colorbar(label='Restoring Temperature (°C)')
plt.title('Restoring Temperature Field')
plt.xlabel('Longitude (degrees)')
plt.ylabel('Latitude (degrees)')
plt.grid()
plt.savefig('SST_relax.png', dpi=300)

# Interpolate tref from baroclinic gyre case to the new grid
tref = [30.,27.,24.,21.,18.,15.,13.,11.,9.,7.,6.,5.,4.,3.,2.]
dzref = [50.,60.,70.,80.,90.,100.,110.,120.,130.,140.,150.,160.,170.,180.,190.]

zref = np.zeros(len(tref))
for i in range(len(tref)):
    if i == 0:
        zref[i] = dzref[i]*0.5
    else:
        zref[i] = zref[i-1] + (dzref[i-1]+dzref[i])*0.5

# Open and load as big-endian float32
with open('dz.bin', "rb") as f:
    dz = np.frombuffer(f.read(), dtype=">f4")  # > = big-endian, f4 = float32
ztarget = np.zeros(len(dz))
for i in range(len(dz)):
    if i == 0:
        ztarget[i] = dz[i]*0.5
    else:
        ztarget[i] = ztarget[i-1] + (dz[i-1]+dz[i])*0.5

# Interpolate tref to the new grid
from scipy.interpolate import interp1d
interp_func = interp1d(zref, tref, bounds_error=False, fill_value="extrapolate")
tref_interp = interp_func(ztarget)
# Save the interpolated tref as big-endian float32
tref_interp.astype('>f4').tofile('tref.bin')

plt.figure(figsize=(10, 6))
plt.plot(tref, -zref, 'o-', label='Original tref', alpha=0.7)
plt.plot(tref_interp, -ztarget, 's-', label='Interpolated tref', alpha=0.7)
plt.xlabel('tref (°C)')
plt.ylabel('Depth (m)')
plt.title('tref Interpolation')
plt.legend()
plt.savefig('tref_interpolation.png', dpi=300)

