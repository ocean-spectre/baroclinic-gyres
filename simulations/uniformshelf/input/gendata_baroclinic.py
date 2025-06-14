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
xs = 300 # location of shelf edge (km)
a = 100.0 # length scale for shelf transition width (1/km)
b = 100.0 # length scale for shelf transition width (1/km)

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
h[1:-1, 1:-1] = -h_shelf[1:-1, 1:-1]  # set ocean depth to shelf depth in interior
# save as single-precision (float32) with big-endian byte ordering
h.astype('>f4').tofile('bathy.bin')

# plot the batymetry
import matplotlib.pyplot as plt
plt.figure(figsize=(10, 6))
plt.imshow(h.transpose(), origin='lower', extent=(xo, xeast, yo, ynorth), cmap='viridis')
plt.colorbar(label='Depth (m)')
plt.title('Bathymetry of the Ocean Domain')
plt.xlabel('Longitude (degrees)')
plt.ylabel('Latitude (degrees)')
plt.grid()
plt.savefig('bathy.png', dpi=300)

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

# Restoring temperature (function of y only,
# from Tmax at southern edge to Tmin at northern edge)
Tmax = 30
Tmin = 0
Trest = (Tmax-Tmin)/(ny-2)/dy * (ynorth-Y) + Tmin # located and computed at YC points
Trest.astype('>f4').tofile('SST_relax.bin')


# #Interpolate tref from baroclinic gyre case to the new grid
# tref = [30.,27.,24.,21.,18.,15.,13.,11.,9.,7.,6.,5.,4.,3.,2.]
# dzref = [50.,60.,70.,80.,90.,100.,110.,120.,130.,140.,150.,160.,170.,180.,190.]

# zref = np.zeros(len(tref))
# for i in range(len(tref)):
#     if i == 0:
#         zref[i] = dzref[i]*0.5
#     else:
#         zref[i] = zref[i-1] + (dzref[i-1]+dzref[i])*0.5

# # Open and load as big-endian float32
# with open('dz.bin', "rb") as f:
#     dz = np.frombuffer(f.read(), dtype=">f4")  # > = big-endian, f4 = float32
# ztarget = np.zeros(len(dz))
# for i in range(len(dz)):
#     if i == 0:
#         ztarget[i] = dz[i]*0.5
#     else:
#         ztarget[i] = ztarget[i-1] + (dz[i-1]+dz[i])*0.5

# # Interpolate tref to the new grid
# from scipy.interpolate import interp1d
# interp_func = interp1d(zref, tref, bounds_error=False, fill_value="extrapolate")
# tref_interp = interp_func(ztarget)
# print(f"Interpolated tref: {tref_interp}")
# # Save the interpolated tref as big-endian float32
# tref_interp.astype('>f4').tofile('tref.bin')