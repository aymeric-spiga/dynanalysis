#! /usr/bin/env python

import numpy as np
from ppclass import pp
import ppcompute
import netCDF4 as nc
import planets

####################################################
fileAP="DRAG90days_DISSIP10000_year1-10_512_every200d_zonmean_stride4lat.nc"
#fileAP="test.nc"
####################################################
p_upper,p_lower,nlev = 4.0e2,2.5e5,40 # whole atm
#p_upper,p_lower,nlev = 3e3, 2e5, 40 # tropo
#p_upper,p_lower,nlev = 5e2, 5e4, 20 # Cassini
targetp1d = np.logspace(np.log10(p_lower),np.log10(p_upper),nlev)
#####################################################
#targetp1d = np.array([5.,10.,20.,50.,100.,200.,500.,1000.,2000.])
#targetp1d = targetp1d*100.
#targetp1d = targetp1d[::-1]
#####################################################
myp = planets.Saturn
day_per_year = 24430.
####################################################
short = False
includels = True
####################################################

#--------------------------------------------------------------------------------------------------------------------------
#--------------------------------------------------------------------------------------------------------------------------
#--------------------------------------------------------------------------------------------------------------------------

####################################################
def interpolate(targetp1d,sourcep3d,fieldsource3d):
  nt,nz,nlat = fieldsource3d.shape
  coordsource3d = -np.log(sourcep3d) # interpolate in logp
  coordtarget1d = -np.log(targetp1d) # interpolate in logp
  nzt = coordtarget1d.size
  fieldtarget3d = np.zeros((nt,nzt,nlat))
  for nnn in range(nlat):
   for ttt in range(nt):
    fieldtarget3d[ttt,:,nnn] = np.interp(coordtarget1d,coordsource3d[ttt,:,nnn],fieldsource3d[ttt,:,nnn],left=np.nan,right=np.nan)
  return fieldtarget3d

####################################################
def fix_time_axis(tdim,period):
  ntt = tdim.size
  tdim = tdim % period 
  nperiod = 0
  corrected_tdim = np.empty(ntt)
  corrected_tdim[0] = float(tdim[0]/period)
  for iii in range(1,ntt):
    if tdim[iii] - tdim[iii-1] < 0: 
      nperiod = nperiod + 1
    corrected_tdim[iii] = float(nperiod) + float(tdim[iii]/period)
  return corrected_tdim

####################################################
def kron2ls(krontab):
  # load Capderou calendar
  jour,kron,Ms,Ls,M,v,declin,equt,ra,distr = np.loadtxt("saturne_calendrier_mod.txt",skiprows=11,unpack=True)
  nnn = kron.size
  # last point is not 0 but 360
  Ls[-1] = 360.
  # duplicate arrays for several years
  # ... with additional offset each year (no modulo)
  nyears = 20
  for yyy in range(nyears):
    kron = np.append(kron,kron[1:nnn]+(day_per_year*(yyy+1)))
    Ls = np.append(Ls,Ls[1:nnn]+(360.*(yyy+1)))
  # interpolate Capderou calendar on array given as input
  lstab = np.interp(krontab,kron,Ls)
  return lstab

####################################################
def addvar(filename,dimname,varname,varfield):
  f = nc.Dataset(filename,'a',format='NETCDF3_CLASSIC')
  var = f.createVariable(varname, 'd', dimname) 
  if   len(dimname) == 4: var[:,:,:,:] = varfield
  elif len(dimname) == 3: var[:,:,:] = varfield
  varfield = None ; var = None
  f.close()
  print "... ... done: "+varname
  return

####################################################
def getp_fromapbp(fileAP):
  aps=pp(file=fileAP,var="aps",x=0,y=0).getf()
  bps=pp(file=fileAP,var="bps",x=0,y=0).getf()
  ps=pp(file=fileAP,var="ps").getf()
  nt,ny,nx = ps.shape
  nz = len(aps)
  p = np.zeros((nt,nz,ny,nx))
  for tt in range(nt):
   for kk in range(nz):
    p[tt,kk,:,:] = aps[kk]+bps[kk]*ps[tt,:,:]
  return ppcompute.mean(p,axis=3)

####################################################
print "... getting pressure field !"
if ispressure:
  press=pp(file=fileAP,var="p",x=charx).getf()
else:
  press=getp_fromapbp(fileAP)

####################################################
print "... getting fields from file !"
u,xdim,ydim,zdim,tdim=pp(file=fileAP,var="u",x=charx).getfd() ; print "... ... done: u"
temp=pp(file=fileAP,var="temp",x=charx).getf() ; print "... ... done: temp"
if 0 == 1:
  ISR=pp(file=fileAP,var="ISR",x=charx).getf() ; print "... ... done: ISR"
  OLR=pp(file=fileAP,var="OLR",x=charx).getf() ; print "... ... done: OLR"
if not short:
  v=pp(file=fileAP,var="v",x=999).getf() ; print "... ... done: v"
  vpup=pp(file=fileAP,var="vpup",x=999).getf() ; print "... ... done: vpup"
  vptp=pp(file=fileAP,var="vptp",x=999).getf() ; print "... ... done: vptp"
  upup=pp(file=fileAP,var="upup",x=999).getf() ; print "... ... done: upup"
  vpvp=pp(file=fileAP,var="vpup",x=999).getf() ; print "... ... done: vpvp" 

####################################################
print "... interpolating !"
u = interpolate(targetp1d,press,u) ; print "... ... done: u"
temp = interpolate(targetp1d,press,temp) ; print "... ... done: temp"
if not short:
  v = interpolate(targetp1d,press,v) ; print "... ... done: v"
  vpup = interpolate(targetp1d,press,vpup) ; print "... ... done: vpup"
  vptp = interpolate(targetp1d,press,vptp) ; print "... ... done: vptp"
  eke = interpolate(targetp1d,press,0.5*(vpvp + upup)) ; print "... ... done: eke"

####################################################
print "... computations !"

# *** DIMENSIONS
nt,nz,nlat = u.shape
nlon = 1

# *** TIME AXIS
tdim = fix_time_axis(tdim,day_per_year)
if includels:
  lstab = kron2ls(tdim*day_per_year)

# *** VERTICAL COORDINATES
# pseudo-altitude (log-pressure) coordinates
pseudoz = myp.pseudoz(targetp1d,p0=targetp1d[0]+1.)
# pressure: from (nz) array to (nt,nz,ny) array
targetp3d = np.tile(targetp1d,(nt,1))
targetp3d = np.tile(np.transpose(targetp3d),(nlat,1,1))
targetp3d = np.transpose(targetp3d)

# *** CURVATURE TERMS ***
lat2d = np.tile(ydim,(nz,1))
acosphi2d = myp.acosphi(lat=lat2d)
cosphi2d = acosphi2d / myp.a
latrad,lat2drad = ydim*np.pi/180.,lat2d*np.pi/180.
beta = myp.beta(lat=lat2d)
f = myp.fcoriolis(lat=lat2d)
print "... ... done: coordinates"

# *** ANGULAR MOMENTUM ***
  # -- see Lauritzen et al. JAMES 2014
  # dV = r^2 cosphi dlambda dphi dr (shallow atm)
  # rho dr = - dp / g (hydrostatic equilibrium)
  # hence dm = rho dV = - r^2 cosphi dlambda dphi dp / g
dlat = np.abs(latrad[1]-latrad[0])
dlon = 2*np.pi
dp = np.zeros((nt,nz,nlat))
dp[:,0:nz-2,:] = targetp3d[:,1:nz-1,:] - targetp3d[:,0:nz-2,:]
dp[:,nz-1,:] = dp[:,nz-2,:] 
dm = - myp.a*acosphi2d * dlon * dlat * dp/myp.g # mass for each considered grid mesh
angmom = dm * myp.angmom(u=u,lat=lat2d) / 1.e25 
# units as in Lauritzen et al. JAMES 2014 E25 kg m2 s-1
# -- plus, a normalization is needed (otherwise overflow absurdities)
print "... ... done: angular momentum"

if not short:

 # *** BASIC DIAGNOSTICS ***
 rho = targetp3d / (myp.R*temp) # density
 tpot = myp.tpot(temp,targetp3d) # potential temperature
 emt = rho*vpup # eddy momentum transport
 # meridional heat flux?rho*vptp
 print "... ... done: basic diagnostics"

 # *** DIAGNOSTICS FOR INSTABILITY
 N2 = np.zeros((nt,nz,nlat)) # static stability
 effbeta_bt = np.zeros((nt,nz,nlat)) # barotropic effective beta
 effbeta_bc = np.zeros((nt,nz,nlat)) # baroclinic effective beta
 ushear = np.zeros((nt,nz,nlat)) # vertical wind shear
 for ttt in range(nt):
   # barotropic effective beta (Rayleigh-Kuo criterion)
   interm = u[ttt,:,:]
   for i in range(2): # d2u/dy2
     interm,dummy = ppcompute.deriv2d(interm*cosphi2d,latrad,targetp1d) / acosphi2d
   effbeta_bt[ttt,:,:] = beta - interm
   # static stability (according to Holton 2004 equation 8.45)
   interm = temp[ttt,:,:]
   dummy,dTdz = ppcompute.deriv2d(interm,latrad,pseudoz)
   N2[ttt,:,:] = (myp.R/myp.H())*( dTdz + ((myp.R/myp.cp)*interm/myp.H()) )
   # baroclinic effective beta (see Holton 2004 sections 8.4.2 equations 8.46 and 8.49)
   interm = u[ttt,:,:]
   for i in range(2):
     dummy,interm = ppcompute.deriv2d(interm,latrad,pseudoz)
     if i==0: 
        ushear[ttt,:,:] = interm
        interm = f*f*rho[ttt,:,:]*interm/N2[ttt,:,:]
   effbeta_bc[ttt,:,:] = effbeta_bt[ttt,:,:] - (interm/rho[ttt,:,:]) 
 print "... ... done: instability"

 # *** EP FLUX and RESIDUAL CIRCULATION
 # *** see Andrews et al. JAS 83
 divFphi = np.zeros((nt,nz,nlat)) # meridional divergence of EP flux
 vstar = np.zeros((nt,nz,nlat)) # residual mean meridional circulation
 EtoM = np.zeros((nt,nz,nlat)) # conversion from eddy to mean
 for ttt in range(nt):
   # (Del Genio et al. 2007) eddy to mean conversion: product emt with du/dy
   du_dy,dummy = ppcompute.deriv2d(u[ttt,:,:]*cosphi2d,latrad,targetp1d) / acosphi2d
   EtoM[ttt,:,:] = emt[ttt,:,:]*du_dy
   # vertical derivatives with pressure
   dummy,dt_dp = ppcompute.deriv2d(temp[ttt,:,:],latrad,targetp1d)
   dummy,du_dp = ppcompute.deriv2d(u[ttt,:,:],latrad,targetp1d)
   # (equation 2.2) psi function
   rcp = myp.R / myp.cp
   psi = - vptp[ttt,:,:] / ( (rcp*temp[ttt,:,:]/targetp3d[ttt,:,:]) - (dt_dp) ) 
   # (equation 2.1) EP flux
   Fphi = acosphi2d * ( - vpup[ttt,:,:] + psi*du_dp ) 
   # (equation 2.3) divergence of EP flux
   divFphi[ttt,:,:],dummy = ppcompute.deriv2d(Fphi*cosphi2d,latrad,targetp1d) / acosphi2d
   # (equation 2.7) equivalent acceleration
   divFphi[ttt,:,:] = divFphi[ttt,:,:] / acosphi2d
   # (equation 2.6) residual mean meridional circulation
   dummy,dpsi_dp = ppcompute.deriv2d(psi,latrad,targetp1d)
   vstar[ttt,:,:] = v[ttt,:,:] - dpsi_dp
 print "... ... done: EP flux"

####################################################
print "... creating the target file !"
f = nc.Dataset("precast.nc",'w',format='NETCDF3_CLASSIC')

xdim = [999.]
dimx = 'longitude'
dimy = 'latitude'
dimt = 'time_counter'
dimz = 'pseudoalt' ## OK with ncview

nam4 = (dimt,dimz,dimy,dimx)
shp4 = (nt,nz,nlat,nlon)
fie4 = (tdim,pseudoz,ydim,xdim)

for iii in range(len(shp4)):
  f.createDimension(nam4[iii],shp4[iii])
  var = f.createVariable(nam4[iii], 'd', nam4[iii])
  var[:] = fie4[iii]
  var = None

if includels:
  var = f.createVariable('Ls', 'd', nam4[0])
  var[:] = lstab
  lstab = None ; var = None

#var = f.createVariable('p', 'd', nam4[1])
#var[:] = targetp1d
## 4D below OK with planetoplot

f.close()

#####################################################
print "... adding 3D variables !"
addvar("precast.nc",nam4,'p',targetp3d)
addvar("precast.nc",nam4,'u',u)
addvar("precast.nc",nam4,'temp',temp)
addvar("precast.nc",nam4,'angmom',angmom)
if not short:
  addvar("precast.nc",nam4,'eke',eke)
  addvar("precast.nc",nam4,'tpot',tpot)
  addvar("precast.nc",nam4,'N2',N2)
  addvar("precast.nc",nam4,'effbeta_bt',effbeta_bt)
  addvar("precast.nc",nam4,'effbeta_bc',effbeta_bc)
  addvar("precast.nc",nam4,'ushear',ushear)
  addvar("precast.nc",nam4,'divFphi',divFphi)
  addvar("precast.nc",nam4,'vstar',vstar)
  addvar("precast.nc",nam4,'EtoM',EtoM)

#####################################################
print "... adding 2D variables !"
namdim2d = (nam4[0],nam4[2],nam4[3])
addvar("precast.nc",namdim2d,'ISR',ISR)
addvar("precast.nc",namdim2d,'OLR',OLR)
