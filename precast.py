#! /usr/bin/env python


import numpy as np
from ppclass import pp
import ppcompute
import netCDF4 as nc
import planets
import time


#####################################################
fileAP="Xhistins_tmp.nc" 
#fileAP="diagfi_tmp.nc" 
outfile = "precast.nc"
#####################################################
vartemp = "temperature"
#vartemp = "temp"
ispressure = False
#####################################################
p_upper,p_lower,nlev = 1.e-1,3.5e5,130 # whole atm
targetp1d = np.logspace(np.log10(p_lower),np.log10(p_upper),nlev)
######################################################
##myp = planets.Saturn
myp = planets.Planet() ; myp.ini("Saturn_dynamico",whereset="./")
#####################################################
short = False
extended = True
includels = True
#####################################################
charx = "0,360" #999: already zonal mean
nopole = False
#####################################################
method = 1 #2
use_spline = False
#####################################################
tpot_alternate = True # calculate tpot before interpolation
is_omega = True
is_gwdparam = False
#####################################################

#--------------------------------------------------------------------------------------------------------------------------
#--------------------------------------------------------------------------------------------------------------------------
#--------------------------------------------------------------------------------------------------------------------------

####################################################
def etape(charvar,time0):
  ttt = round(time.time()-time0,2)
  print("TIME=",ttt,"... ... done: "+charvar)

####################################################
def interpolate(targetp1d,sourcep3d,fieldsource3d,spline=False):
  if spline:
    from scipy import interpolate
  nt,nz,nlat = fieldsource3d.shape
  coordsource3d = -np.log(sourcep3d) # interpolate in logp
  coordtarget1d = -np.log(targetp1d) # interpolate in logp
  nzt = coordtarget1d.size
  fieldtarget3d = np.zeros((nt,nzt,nlat))
  for nnn in range(nlat):
   for ttt in range(nt):
    xs = coordsource3d[ttt,:,nnn]
    ys = fieldsource3d[ttt,:,nnn]
    if not spline:
      fieldtarget3d[ttt,:,nnn] = np.interp(coordtarget1d,xs,ys,left=np.nan,right=np.nan)
    else:
      #tck = interpolate.splrep(xs, ys, s=0)
      #fieldtarget3d[ttt,:,nnn] = interpolate.splev(coordtarget1d, tck, der=0)
      kk = "linear" #"cubic" #"quadratic"
      ff = interpolate.interp1d(xs, ys, kind=kk, bounds_error=False)
      fieldtarget3d[ttt,:,nnn] = ff(coordtarget1d)
  return fieldtarget3d

####################################################
def interpolate4(targetp1d,sourcep3d,fieldsource3d,spline=False):
  if spline: 
    from scipy import interpolate
  nt,nz,nlat,nlon = fieldsource3d.shape
  coordsource3d = -np.log(sourcep3d) # interpolate in logp
  coordtarget1d = -np.log(targetp1d) # interpolate in logp
  nzt = coordtarget1d.size
  fieldtarget3d = np.zeros((nt,nzt,nlat,nlon))
  for mmm in range(nlon):
   for nnn in range(nlat):
    for ttt in range(nt):
     xs = coordsource3d[ttt,:,nnn,mmm]
     ys = fieldsource3d[ttt,:,nnn,mmm]
     if not spline:
       fieldtarget3d[ttt,:,nnn,mmm] = np.interp(coordtarget1d,xs,ys,left=np.nan,right=np.nan)
     else:
       tck = interpolate.splrep(xs, ys, s=0)
       fieldtarget3d[ttt,:,nnn,mmm] = interpolate.splev(coordtarget1d, tck, der=0)
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

#####################################################
#def kron2ls(krontab):
#  # load Capderou calendar
#  jour,kron,Ms,Ls,M,v,declin,equt,ra,distr = np.loadtxt("saturne_calendrier_mod.txt",skiprows=11,unpack=True)
#  nnn = kron.size
#  # last point is not 0 but 360
#  Ls[-1] = 360.
#  # duplicate arrays for several years
#  # ... with additional offset each year (no modulo)
#  nyears = 20
#  for yyy in range(nyears):
#    kron = np.append(kron,kron[1:nnn]+(day_per_year*(yyy+1)))
#    Ls = np.append(Ls,Ls[1:nnn]+(360.*(yyy+1)))
#  # interpolate Capderou calendar on array given as input
#  lstab = np.interp(krontab,kron,Ls)
#  return lstab

####################################################
def addvar(filename,dimname,varname,varfield,time0=None):
  f = nc.Dataset(filename,'a',format='NETCDF3_CLASSIC')
  var = f.createVariable(varname, 'd', dimname) 
  if   len(dimname) == 4: var[:,:,:,:] = varfield
  elif len(dimname) == 3: var[:,:,:] = varfield
  varfield = None ; var = None
  f.close()
  if time0 is not None:
    etape(varname,time0)
  return

####################################################
def getp_fromapbp(fileAP):
  try:
    aps=pp(file=fileAP,var="aps",x=0,y=0).getf()
    bps=pp(file=fileAP,var="bps",x=0,y=0).getf()
    nz = len(aps)
  except:
    print("info: read apbp.txt")
    ap,bp = np.loadtxt("apbp.txt",unpack=True)
    nz = len(ap)
    aps = 0.5*(ap[0:nz-1]+ap[1:nz])
    bps = 0.5*(bp[0:nz-1]+bp[1:nz])
    nz = len(aps)
  #print("... ps")
  ps=pp(file=fileAP,var="ps").getf()
  nt,ny,nx = ps.shape
  p = np.zeros((nt,nz,ny,nx))
  if method == 1:
    ps=ppcompute.mean(ps,axis=2)
    p = np.zeros((nt,nz,ny))
  #print("... compute p")
  for tt in range(nt):
   for kk in range(nz):
    if method == 1:
      p[tt,kk,:] = aps[kk]+bps[kk]*ps[tt,:]
    elif method == 2:
      p[tt,kk,:,:] = aps[kk]+bps[kk]*ps[tt,:,:]
  return p
  #return ppcompute.mean(p,axis=3)

####################################################
def correctnearzero(field):
  # ... e.g. for values very near zero in the neutral troposphere (stability)
  # ... filter out to avoid e.g. infinite values when dividing by this term
  # ... we use the near-zero slightly negative values
  # ... to learn where to discard near-zero values (set to NaN)
  negvalue = np.min(field[np.isfinite(field)])
  val = 2.
  removed = -val*negvalue
  w = np.where(np.abs(field) <= removed)
  field[w] = np.nan
  print("absolute values below this value are set to NaN", removed)
  return field


####################################################
####################################################
####################################################
####################################################


####################################################
time0 = time.time()

####################################################
if ispressure:
  press=pp(file=fileAP,var="p",x=charx).getf()
else:
  press=getp_fromapbp(fileAP)
etape("pressure field",time0)

####################################################
print("... getting fields from file !")
if method == 1:
 u,xdim,ydim,zdim,tdim=pp(file=fileAP,var="u",x=charx).getfd() ; etape("u",time0)
 temp=pp(file=fileAP,var=vartemp,x=charx).getf() ; etape(vartemp,time0)
elif method == 2:
 u,xdim,ydim,zdim,tdim=pp(file=fileAP,var="u").getfd() ; etape("u",time0)
 temp=pp(file=fileAP,var=vartemp).getf() ; etape(vartemp,time0)
if tpot_alternate:
 tpot = myp.tpot(temp,press,p0=targetp1d[0]+1.) 
#if 0 == 1:
#  ISR=pp(file=fileAP,var="ISR",x=charx).getf() ; print("... ... done: ISR")
#  OLR=pp(file=fileAP,var="OLR",x=charx).getf() ; print("... ... done: OLR")
if not short:
 if method == 2:
   v=pp(file=fileAP,var="v").getf() ; etape("v",time0)
   if is_omega:
     o=pp(file=fileAP,var="omega").getf() ; etape("omega",time0)
 elif method == 1:
   v=pp(file=fileAP,var="v",x=charx).getf() ; etape("v",time0)
   if is_omega:
     o=pp(file=fileAP,var="omega",x=charx).getf() ; etape("omega",time0)
   if is_gwdparam:
     east_gwstress=pp(file=fileAP,var="east_gwstress",x=charx).getf() ; etape("east_gwstress",time0)
     west_gwstress=pp(file=fileAP,var="west_gwstress",x=charx).getf() ; etape("west_gwstress",time0)
   print("... coupled terms")
   if charx == "999":
     vpup=pp(file=fileAP,var="vpup",x=charx).getf() ; etape("vpup",time0)
     vptp=pp(file=fileAP,var="vptp",x=charx).getf() ; etape("vptp",time0)
     upup=pp(file=fileAP,var="upup",x=charx).getf() ; etape("upup",time0)
     vpvp=pp(file=fileAP,var="vpvp",x=charx).getf() ; etape("vpvp",time0)
   else:
     staru4D=pp(file=fileAP,var="u",compute="pert_x",x=charx).getf() ; etape("staru4D",time0)
     starv4D=pp(file=fileAP,var="v",compute="pert_x",x=charx).getf() ; etape("starv4D",time0)
     start4D=pp(file=fileAP,var=vartemp,compute="pert_x",x=charx).getf() ; etape("start4D",time0)
     vpup=ppcompute.mean(starv4D*staru4D,axis=3) ; etape("vpup",time0)
     vptp=ppcompute.mean(starv4D*start4D,axis=3) ; etape("vptp",time0)
     upup=ppcompute.mean(staru4D*staru4D,axis=3) ; etape("upup",time0)
     vpvp=ppcompute.mean(starv4D*starv4D,axis=3) ; etape("vpvp",time0)
     if is_omega:
       staro4D=pp(file=fileAP,var="omega",compute="pert_x",x=charx).getf() ; etape("staro4D",time0)
       opup=ppcompute.mean(staro4D*staru4D,axis=3) ; etape("opup",time0)
       optp=ppcompute.mean(staro4D*start4D,axis=3) ; etape("optp",time0)
       del staro4D
     del staru4D ; del starv4D ; del start4D

####################################################
print("... interpolating !")
if method == 1:
  u = interpolate(targetp1d,press,u,spline=use_spline) ; etape("u",time0)
  #temp = interpolate(targetp1d,press,temp,spline=use_spline) ; etape(vartemp,time0)
  if tpot_alternate:
    tpot = interpolate(targetp1d,press,tpot,spline=use_spline) ; etape("tpot",time0)
  else:
    temp = interpolate(targetp1d,press,temp,spline=use_spline) ; etape(vartemp,time0)
  if not short:
    v = interpolate(targetp1d,press,v,spline=use_spline) ; etape("v",time0)
    vpup = interpolate(targetp1d,press,vpup,spline=use_spline) ; etape("vpup",time0)
    vptp = interpolate(targetp1d,press,vptp,spline=use_spline) ; etape("vptp",time0)
    if is_omega:
      o = interpolate(targetp1d,press,o,spline=use_spline) ; etape("omega",time0)
      opup = interpolate(targetp1d,press,opup,spline=use_spline) ; etape("opup",time0)
      optp = interpolate(targetp1d,press,optp,spline=use_spline) ; etape("optp",time0)
    if is_gwdparam:
      east_gwstress=interpolate(targetp1d,press,east_gwstress,spline=use_spline) ; etape("east_gwstress",time0)
      west_gwstress=interpolate(targetp1d,press,west_gwstress,spline=use_spline) ; etape("west_gwstress",time0)
    eke = interpolate(targetp1d,press,0.5*(vpvp + upup),spline=use_spline) ; etape("eke",time0)
elif method == 2:
  u = interpolate4(targetp1d,press,u,spline=use_spline)
  um = ppcompute.mean(u,axis=3) ; etape("u",time0)
  temp = interpolate4(targetp1d,press,temp,spline=use_spline)
  tm = ppcompute.mean(temp,axis=3) ; etape(vartemp,time0)
  if tpot_alternate:
     tpot = interpolate4(targetp1d,press,tpot,spline=use_spline) 
  if not short:
     v = interpolate4(targetp1d,press,v,spline=use_spline)
     vm = ppcompute.mean(v,axis=3) ; etape("v",time0)
     vum = ppcompute.mean(v*u,axis=3) ; etape("vum",time0)
     vtm = ppcompute.mean(v*temp,axis=3) ; etape("vtm",time0)
     utm = ppcompute.mean(u*temp,axis=3) ; etape("utm",time0)
     uum = ppcompute.mean(u*u,axis=3) ; etape("uum",time0)
     vvm = ppcompute.mean(v*v,axis=3) ; etape("vvm",time0)
     if is_omega:
       o = interpolate4(targetp1d,press,o,spline=use_spline)
       om = ppcompute.mean(o,axis=3) ; etape("omega",time0)
       oum = ppcompute.mean(o*u,axis=3) ; etape("oum",time0)
       del o
     del v
     # [u'v'] = [uv] - [u][v] en temporel
     vpup = vum - vm*um ; del vum ; etape("vpup",time0)
     vptp = vtm - vm*tm ; del vtm ; etape("vptp",time0)
     eke = 0.5*((uum - um*um) + (vvm - vm*vm)) ; del uum ; del vvm ; etape("eke",time0)
     v = vm ; del vm
     if is_omega:
       opup = oum - om*um ; del oum ; etape("opup",time0)
       o = om ; del om
  ##
  del press ; del u ; del temp
  u = um ; del um
  temp = tm ; del tm

####################################################
print("... computations !")

# *** DIMENSIONS
nt,nz,nlat = u.shape
nlon = 1

# *** TIME AXIS
if includels:
 if myp.name == "Saturn":
  ##lstab = kron2ls(tdim*day_per_year) # vieux fichiers
  lstab = pp(file=fileAP,var="ls",x=0,y=0,z=0).getf()
  lstab = lstab*180./np.pi
  #lstab = fix_time_axis(lstab,360.) # in years
 else:
  day_per_year = np.ceil(myp.dayperyear())
  tdim = fix_time_axis(tdim,day_per_year)
  lstab = np.zeros(nt)

# *** VERTICAL COORDINATES
# pseudo-altitude (log-pressure) coordinates
pseudoz = myp.pseudoz(targetp1d,p0=targetp1d[0]+1.)
# pressure: from (nz) array to (nt,nz,ny) array
targetp3d = np.tile(targetp1d,(nt,1))
targetp3d = np.tile(np.transpose(targetp3d),(nlat,1,1))
targetp3d = np.transpose(targetp3d)

# *** CURVATURE TERMS ***
if method == 2:
  ydim = ydim[:,0]
lat2d = np.tile(ydim,(nz,1))
acosphi2d = myp.acosphi(lat=lat2d)
cosphi2d = acosphi2d / myp.a
latrad,lat2drad = ydim*np.pi/180.,lat2d*np.pi/180.
beta = myp.beta(lat=lat2d)
f = myp.fcoriolis(lat=lat2d)
tanphia = myp.tanphia(lat=lat2d)
etape("coordinates",time0)

# *** ANGULAR MOMENTUM ***
  # -- see Lauritzen et al. JAMES 2014
  # dV = r^2 cosphi dlambda dphi dr (shallow atm)
  # rho dr = - dp / g (hydrostatic equilibrium)
  # hence dm = rho dV = - r^2 cosphi dlambda dphi dp / g
dlat = np.abs(latrad[1]-latrad[0])
dlon = 2*np.pi
dp = np.gradient(targetp3d,axis=1,edge_order=2)
dm = - myp.a*acosphi2d * dlon * dlat * dp/myp.g # mass for each considered grid mesh #should have glat!
wangmomperumass = myp.wangmom(u=u,lat=lat2d) # wind angular momentum
angmomperumass = myp.angmom(u=u,lat=lat2d)
angmom = dm * angmomperumass / 1.e25
wangmom = dm * wangmomperumass / 1.e25
# units as in Lauritzen et al. JAMES 2014 E25 kg m2 s-1
# -- plus, a normalization is needed (otherwise overflow absurdities)
superindex = myp.superrot(u=u,lat=lat2d)
etape("angular momentum",time0)

# *** BASIC DIAGNOSTICS ***
if not tpot_alternate:
    tpot = myp.tpot(temp,targetp3d,p0=targetp1d[0]+1.) # potential temperature
else:
    temp = myp.invtpot(tpot,targetp3d,p0=targetp1d[0]+1.)

##########################
## EXTENDED DIAGNOSTICS ##
##########################
if not short:

 rho = targetp3d / (myp.R*temp) # density
 emt = rho*vpup # eddy momentum transport
 amt_mmc_v = v*wangmom # meridional angular momentum transport by mean meridional circulation
 mpvpperumass = myp.angmom(u=vpup,lat=lat2d) # contributions from transients waves in the total meridional transport
 mpvp = dm * mpvpperumass /1.e25
 #if not tpot_alternate:
 #  tpot = myp.tpot(temp,targetp3d,p0=targetp1d[0]+1.) # potential temperature
 ## meridional heat flux?rho*vptp

 # *** Thermal transport by MMC ***
 temp_mmc_v = temp * v
 tpot_mmc_v = tpot * v
 etape("basic diagnostics",time0)
 etape("please wait for extended computations...",time0)

 # *** MASS STREAMFUNCTION ***
 # *** AND VERTICAL VELOCITY ***
 # NB: slide 7 in https://atmos.washington.edu/~dennis/501/501_Gen_Circ_Atmos.pdf
 # term = 2 pi a cosphi / g
 # --> PSIM = term * int_0^p v dp
 import scipy
 import scipy.integrate
 psim = np.zeros((nt,nz,nlat)) # mass streamfunction
 omega = np.zeros((nt,nz,nlat)) # vertical velocity in pressure coordinate
 alph = 2.*np.pi*acosphi2d/myp.g
 w = np.isnan(v) # save NaN locations 
 v[w] = 0. # necessary otherwise integrations fail
 # integration loop
 x = targetp1d[:] # coordinate
 #x = np.insert(x,0,0) # JL: integrate from p=0 towards p
 x = np.append(x,0) # JL: integrate from p=0 towards p
 for ttt in range(nt):
  for yyy in range(nlat):
   y = v[ttt,:,yyy] # integrand
   #y = np.insert(y,0,y[0]) # JL: integrate from p=0 towards p
   y = np.append(y,y[-1]) # JL: integrate from p=0 towards p
   for zzz in range(0,nz):
#     the minus sign below comes from the fact that x is ordered by decreasing values of p
#           whereas the integral should be performed from 0 to p. 
     psim[ttt,zzz,yyy] = -scipy.integrate.simps(y[zzz:],x[zzz:])*alph[0,yyy]
     #psim[ttt,zzz,yyy] = scipy.integrate.simps(y[0:zzz+1],x[0:zzz+1])*alph[0,yyy]
 # reset to NaN after integration
 v[w] = np.nan ; psim[w] = np.nan
 etape("streamfunction",time0)
 if not is_omega:
 # derivatives of streamfunction --> velocity (notably omega)
  for ttt in range(nt):
    dpsim_dp,dpsim_dphi = np.gradient(psim[ttt,:,:],targetp1d,latrad,edge_order=2)/alph  
    # meridional: v = 1/term dPSIM/dp
    vphi = dpsim_dp
    # vertical: omega = (-1/a) 1/term dPSIM/dphi
    omega[ttt,:,:] = -dpsim_dphi/myp.a
    ##CHECK against actual v
    #import ppplot ; pl = ppplot.plot2d()
    #pl.f, pl.x, pl.y = vphi, ydim, pseudoz ; pl.title = r'$d\Psi_M/dp$' 
    #pl.makesave(mode="png",filename="v_from_streamfunction") 
    #pl.f = v[ttt,:,:] ; pl.title = r'v'
    #pl.makesave(mode="png",filename="v_actual")
    #pl.f = v[ttt,:,:]-vphi[:,:] ; pl.title = r'v - $d\Psi_M/dp$'
    #pl.makesave(mode="png",filename="v_diff")
    #print("max diff:",ppcompute.max(v[ttt,:,:]-vphi[:,:]))
  etape("vertical velocity from streamfunction",time0)
 else:
  omega = o

 # *** DIAGNOSTICS USING VERTICAL VELOCITY (now available from either streamfunction or file)
 amt_mmc_w = omega*wangmom # vertical angular momentum transport by mean meridional circulation
 temp_mmc_w = temp * omega
 tpot_mmc_w = tpot * omega

 # *** DIAGNOSTICS FOR INSTABILITY
 N2 = np.zeros((nt,nz,nlat)) # static stability
 effbeta_bt = np.zeros((nt,nz,nlat)) # barotropic effective beta
 effbeta_bc = np.zeros((nt,nz,nlat)) # baroclinic effective beta
 ushear = np.zeros((nt,nz,nlat)) # vertical wind shear
 for ttt in range(nt):
   # barotropic effective beta (Rayleigh-Kuo criterion)
   interm = u[ttt,:,:]
   for i in range(2): # d2u/dy2
     dummy,interm = np.gradient(interm*cosphi2d,targetp1d,latrad,edge_order=2) / acosphi2d
   effbeta_bt[ttt,:,:] = beta - interm
   # static stability (according to Holton 2004 equation 8.45)
   interm = temp[ttt,:,:]
   dTdz,dummy = np.gradient(interm,pseudoz,latrad,edge_order=2)  
   N2[ttt,:,:] = (myp.R/myp.H())*( dTdz + ((myp.R/myp.cp)*interm/myp.H()) )
   # ... this term is very near zero in the neutral troposphere
   # ... so this needs to be filtered out, not to get infinite values
   N2[ttt,:,:] = correctnearzero(N2[ttt,:,:])
   # baroclinic effective beta (see Holton 2004 sections 8.4.2 equations 8.46 and 8.49)
   interm = u[ttt,:,:]
   for i in range(2):
     interm,dummy = np.gradient(interm,pseudoz,latrad,edge_order=2) 
     if i==0: 
        ushear[ttt,:,:] = interm
        interm = f*f*rho[ttt,:,:]*interm/N2[ttt,:,:]
   effbeta_bc[ttt,:,:] = effbeta_bt[ttt,:,:] - (interm/rho[ttt,:,:])
   # recompute static stability from tpot for outputs
   interm = tpot[ttt,:,:]
   dTdz,dummy = np.gradient(interm,pseudoz,latrad,edge_order=2)
   N2[ttt,:,:] = (myp.g/interm)*dTdz
   ### TEST
   #interm = u[ttt,:,:]
   #dummy,interm = ppcompute.deriv2d(interm,latrad,targetp1d)
   #interm = interm*f*f*rho[ttt,:,:]*rho[ttt,:,:]*myp.g*myp.g/N2[ttt,:,:]
   #dummy,interm = ppcompute.deriv2d(interm,latrad,targetp1d)
   #effbeta_bc[ttt,:,:] = effbeta_bt[ttt,:,:] - interm
 etape("instability",time0)

 if extended:
     # *** EP FLUX and RESIDUAL CIRCULATION
     # *** see Andrews et al. JAS 83
     Fphi = np.zeros((nt,nz,nlat)) # EP flux H
     Fp = np.zeros((nt,nz,nlat)) # EP flux V
     Fphi_simp = np.zeros((nt,nz,nlat)) # EP flux H simplified
     Fp_simp = np.zeros((nt,nz,nlat)) # EP flux V simplified
     Fp_simp_eq = np.zeros((nt,nz,nlat)) # EP flux V simplified adapted for equatorial regions
     Tphi = np.zeros((nt,nz,nlat)) # meridional divergence of thermal flux
     Tphi_TEM = np.zeros((nt,nz,nlat)) # meridional divergence of thermal flux
     Tp = np.zeros((nt,nz,nlat)) # vertical divergence of thermal flux
     psi = np.zeros((nt,nz,nlat))
     divFphi = np.zeros((nt,nz,nlat)) # meridional divergence of EP flux
     divFphi_simp = np.zeros((nt,nz,nlat)) # meridional divergence of EP flux simplified
     divFp = np.zeros((nt,nz,nlat)) # vertical divergence of EP flux (usually small)
     divFp_simp_eq = np.zeros((nt,nz,nlat)) # vertical divergence of EP flux simplified for equatorial regions (usually small)
     EtoM = np.zeros((nt,nz,nlat)) # conversion from eddy to mean
     vstar = np.zeros((nt,nz,nlat)) # residual mean meridional circulation
     omegastar = np.zeros((nt,nz,nlat)) # residual mean vertical circulation

     accrmc_TEM = np.zeros((nt,nz,nlat)) # total acceleration by residual mean circulation in Transformed Eulerian-mean formalism
     mass_accrmc_TEM = np.zeros((nt,nz,nlat)) # total acceleration by residual mean circulation in Transformed Eulerian-mean formalism
     accrmch_TEM = np.zeros((nt,nz,nlat)) # horizontal acceleration by residual mean circulation in Transformed Eulerian-mean formalism
     accrmcv_TEM = np.zeros((nt,nz,nlat)) # vertical acceleration by residual mean circulation in Transformed Eulerian-mean formalism
     accedd_TEM = np.zeros((nt,nz,nlat)) # total eddies acceleration in Transformed Eulerian-mean formalism
     mass_accedd_TEM = np.zeros((nt,nz,nlat)) # total acceleration by residual mean circulation in Transformed Eulerian-mean formalism
     acceddh_TEM = np.zeros((nt,nz,nlat)) # horizontal eddies acceleration in Transformed Eulerian-mean formalism
     acceddv_TEM = np.zeros((nt,nz,nlat)) # vertical eddies acceleration in Transformed Eulerian-mean formalism
     dudt_TEM = np.zeros((nt,nz,nlat)) # Total acceleration in Transformed Eulerian-mean formalism
     temprmc_TEM = np.zeros((nt,nz,nlat)) # Total thermal flux by the residual mean circulation in Transformed Eulerian-mean formalism
     temprmch_TEM = np.zeros((nt,nz,nlat)) # Horizontal thermal flux by the residual mean circulation in Transformed Eulerian-mean formalism
     temprmcv_TEM = np.zeros((nt,nz,nlat)) # Vertical thermal flux by the residual mean circulation in Transformed Eulerian-mean formalism
     tempedd_TEM = np.zeros((nt,nz,nlat)) # Total thermal flux by eddies in Transformed Eulerian-mean formalism
     tempeddh_TEM = np.zeros((nt,nz,nlat)) # Horizontal thermal flux by eddies in Transformed Eulerian-mean formalism
     tempeddv_TEM = np.zeros((nt,nz,nlat)) # Vertical thermal flux by eddies in Transformed Eulerian-mean formalism
     dTdt_TEM = np.zeros((nt,nz,nlat)) # total thermal evolution in Transformed Eulerian-mean formalism
     psim_TEM = np.zeros((nt,nz,nlat)) # transformed Eulerian mean streamfunction (seviour et al 2012)
     wave_drag = np.zeros((nt,nz,nlat)) # zonal-mean forces due to waves drag using psi_TEM (seviour et al 2012)

     ### Simple formlation of TEM formalism:
     accedd_TEM_simp = np.zeros((nt,nz,nlat))
     acceddh_TEM_simp = np.zeros((nt,nz,nlat))
     acceddv_TEM_simp = np.zeros((nt,nz,nlat))

     accrmc_CEM = np.zeros((nt,nz,nlat)) # acceleration by residual mean circulation in Classical Eulerian-mean formalism
     accrmch_CEM = np.zeros((nt,nz,nlat)) # horizontal acceleration by residual mean circulation in Classical Eulerian-mean formalism
     accrmcv_CEM = np.zeros((nt,nz,nlat)) # vertical acceleration by residual mean circulation in Classical Eulerian-mean formalism
     accedd_CEM = np.zeros((nt,nz,nlat)) # acceleration by eddies in Classical Eulerian-mean formalism
     acceddh_CEM = np.zeros((nt,nz,nlat)) # horizontal acceleration by eddies in Classical Eulerian-mean formalism
     acceddv_CEM = np.zeros((nt,nz,nlat)) # vertical acceleration by eddies in Classical Eulerian-mean formalism
     dudt_CEM = np.zeros((nt,nz,nlat)) # total acceleration in Classical Eulerian-mean formalism
     dTdt_CEM = np.zeros((nt,nz,nlat)) # total thermal evolution in Classical Eulerian-mean formalism
     temprmc_CEM = np.zeros((nt,nz,nlat)) # thermal flux transported by residual mean circulation in Classical Eulerian-mean formalism
     temprmch_CEM = np.zeros((nt,nz,nlat)) # horizontal thermal flux transported by residual mean circulation in Classical Eulerian-mean formalism
     temprmcv_CEM = np.zeros((nt,nz,nlat)) # vertical thermal flux transported by residual mean circulation in Classical Eulerian-mean formalism
     tempedd_CEM = np.zeros((nt,nz,nlat)) # thermal flux transported by eddy circulation
     tempeddh_CEM = np.zeros((nt,nz,nlat)) # horizontal thermal flux transported by eddy circulation
     tempeddv_CEM = np.zeros((nt,nz,nlat)) # vertical thermal flux transported by eddy circulation

     for ttt in range(nt):
       dummy,dt_dy = np.gradient(temp[ttt,:,:],targetp1d,latrad,edge_order=2)
       # (Del Genio et al. 2007) eddy to mean conversion: product emt with du/dy
       dummy,du_dy = np.gradient(u[ttt,:,:]*cosphi2d,targetp1d,latrad,edge_order=2) / acosphi2d 
       EtoM[ttt,:,:] = vpup[ttt,:,:]*du_dy #emt[ttt,:,:]*du_dy
       # vertical derivatives with pressure
       dt_dp,dummy = np.gradient(temp[ttt,:,:],targetp1d,latrad,edge_order=2) 
       du_dp,dummy = np.gradient(u[ttt,:,:],targetp1d,latrad,edge_order=2) 
       ####################################
       # (equation 2.2) psi function
       rcp = myp.R / myp.cp
       # ... formula for psi is divided by a stability term
       stabterm = (rcp*temp[ttt,:,:]/targetp3d[ttt,:,:]) - (dt_dp)
       # ... this term is very near zero in the neutral troposphere
       # ... so this needs to be filtered out, not to get infinite values
       stabterm = correctnearzero(stabterm)
       # ... finally we calculate psi
       psi[ttt,:,:] = - vptp[ttt,:,:] / stabterm 
       ####################################
       # (equation 2.1) EP flux (phi)
       Fphi[ttt,:,:] = acosphi2d * ( - vpup[ttt,:,:] + psi[ttt,:,:]*du_dp ) 
       # EP flux (phi) simplified to make an EP flux diagram (see Vallis pp 582 Second Ed.)
       Fphi_simp[ttt,:,:] = - acosphi2d * vpup[ttt,:,:] 
       # (equation 2.1) EP flux (p)
       if is_omega:
         verteddy = - opup[ttt,:,:]
       else:
         verteddy = 0. # often a acceptable approximation
       Fp[ttt,:,:] = - acosphi2d * ( verteddy + psi[ttt,:,:] * (du_dy - f) )   
       # EP flux (p) simplified to make an EP flux diagram (see Vallis pp 582 Second Ed.)
       Fp_simp[ttt,:,:] = acosphi2d * psi[ttt,:,:] * f  
       if is_omega:
          Fp_simp_eq[ttt,:,:] = - acosphi2d * opup[ttt,:,:] #for equatorial regions, we keep equatorial waves contribution: opup 
       # (equation 2.3) divergence of EP flux
       dummy,divFphi[ttt,:,:] = np.gradient(Fphi[ttt,:,:]*cosphi2d,targetp1d,latrad,edge_order=2) / acosphi2d  
       divFp[ttt,:,:],dummy = np.gradient(Fp[ttt,:,:],targetp1d,latrad,edge_order=2) 
       # divergence of EP flux simplified
       dummy,divFphi_simp[ttt,:,:] = np.gradient(Fphi_simp[ttt,:,:]*cosphi2d,targetp1d,latrad,edge_order=2) / acosphi2d
       divFp_simp_eq[ttt,:,:],dummy = np.gradient(Fp_simp_eq[ttt,:,:],targetp1d,latrad,edge_order=2)
       # (equation 2.6) residual mean meridional circulation
       dpsi_dp,dummy = np.gradient(psi[ttt,:,:],targetp1d,latrad,edge_order=2)  
       vstar[ttt,:,:] = v[ttt,:,:] - dpsi_dp
       dummy,dpsi_dy = np.gradient(psi[ttt,:,:]*cosphi2d,targetp1d,latrad,edge_order=2) / acosphi2d
       if is_omega:
           omegastar[ttt,:,:] = omega[ttt,:,:] + dpsi_dy
       # (F. Lott lessons) divergence of turbulent thermal flux
       dummy,Tphi[ttt,:,:] = np.gradient(vptp[ttt,:,:]*cosphi2d,targetp1d,latrad,edge_order=2) / acosphi2d
       Tphi_TEM[ttt,:,:],dummy = np.gradient(vptp[ttt,:,:]*dt_dy/(myp.a*stabterm),targetp1d,latrad,edge_order=2)
       if is_omega:
           Tp[ttt,:,:],dummy = np.gradient(optp[ttt,:,:],targetp1d,latrad,edge_order=2)
       # (equation 2.7) Transformed Eulerian-mean for zonal momentum equation (eddies)
       acceddh_TEM[ttt,:,:] = divFphi[ttt,:,:] / acosphi2d
       acceddv_TEM[ttt,:,:] = divFp[ttt,:,:] / acosphi2d
       accedd_TEM[ttt,:,:] = (divFphi[ttt,:,:] + divFp[ttt,:,:]) / acosphi2d
       # Transformed Eulerian-mean for zonal momentum equation (simple formulation)
       acceddh_TEM_simp[ttt,:,:] = divFphi_simp[ttt,:,:] / acosphi2d
       acceddv_TEM_simp[ttt,:,:] = divFp_simp_eq[ttt,:,:] / acosphi2d
       accedd_TEM_simp[ttt,:,:] = (divFphi_simp[ttt,:,:] + divFp_simp_eq[ttt,:,:]) / acosphi2d

       # (equation 2.7) Transformed Eulerian-mean for zonal momentum equation (residual meridional circulation)
       accrmch_TEM[ttt,:,:] = - ((du_dy - f) * vstar[ttt,:,:])
       accrmcv_TEM[ttt,:,:] = - (du_dp*omegastar[ttt,:,:])
       accrmc_TEM[ttt,:,:] = - ((du_dy - f) * vstar[ttt,:,:]) - (du_dp*omegastar[ttt,:,:])
       dudt_TEM[ttt,:,:] = accrmc_TEM[ttt,:,:] + accedd_TEM[ttt,:,:]

       #TEM * layer mass to highlight lower level
       mass_accedd_TEM[ttt,:,:] = accedd_TEM[ttt,:,:] * dm[ttt,:,:] / 1.e25
       mass_accrmc_TEM[ttt,:,:] = accrmc_TEM[ttt,:,:] * dm[ttt,:,:] / 1.e25

       # (F. Lott lessons, chap 3) Transformed Eulerian-mean for thermodynamics equation (residual mean circulation)
       temprmch_TEM[ttt,:,:] = - ((dt_dy / myp.a)*vstar[ttt,:,:])
       temprmcv_TEM[ttt,:,:] = - (dt_dp*omegastar[ttt,:,:])
       temprmc_TEM[ttt,:,:] = - ((dt_dy / myp.a)*vstar[ttt,:,:]) - (dt_dp*omegastar[ttt,:,:])
       # (F. Lott lessons, chap 3) Transformed Eulerian-mean for thermodynamics equation (eddies)
       tempeddh_TEM[ttt,:,:] = - Tphi_TEM[ttt,:,:]
       tempeddv_TEM[ttt,:,:] = - Tp[ttt,:,:]
       tempedd_TEM[ttt,:,:] = - Tphi_TEM[ttt,:,:] - Tp [ttt,:,:]
       dTdt_TEM[ttt,:,:] = temprmc_TEM[ttt,:,:] + tempedd_TEM[ttt,:,:]

       # (equation 2.5) classical Eulerian-mean for zonal momentum equation (residual mean circulation)
       accrmch_CEM[ttt,:,:] = - (du_dy - f)*v[ttt,:,:]
       accrmcv_CEM[ttt,:,:] = - du_dp*omega[ttt,:,:]
       accrmc_CEM[ttt,:,:] = - (du_dy - f)*v[ttt,:,:] - du_dp*omega[ttt,:,:]
       # (equation 2.5) classical Eulerian-mean for zonal momentum equation (eddies)
       dummy,ddd = np.gradient(vpup[ttt,:,:]*cosphi2d*cosphi2d,targetp1d,latrad,edge_order=2)
       if is_omega:
         ddd2,dummy = np.gradient(opup[ttt,:,:],targetp1d,latrad,edge_order=2)
       else:
         ddd2 = 0.
       acceddh_CEM[ttt,:,:] =  - ddd / acosphi2d / cosphi2d
       acceddv_CEM[ttt,:,:] = - ddd2
       accedd_CEM[ttt,:,:] = - ddd2 - ddd / acosphi2d / cosphi2d
       dudt_CEM[ttt,:,:] = accrmc_CEM[ttt,:,:] + accedd_CEM[ttt,:,:]
       # (F. Lott lessons, chap 3) classical Eulerian-mean for thermodynamics equation (residual mean circulation)
       temprmc_CEM[ttt,:,:] = - ((dt_dy / myp.a)*v[ttt,:,:]) - (dt_dp*omega[ttt,:,:])
       temprmch_CEM[ttt,:,:] = - ((dt_dy / myp.a)*v[ttt,:,:])
       temprmcv_CEM[ttt,:,:] = - (dt_dp*omega[ttt,:,:])
       # (F. Lott lessons, chap 3) classical Eulerian-mean for thermodynamics equation (eddies)
       tempedd_CEM[ttt,:,:] = - Tphi[ttt,:,:] - Tp[ttt,:,:]
       tempeddh_CEM[ttt,:,:] = - Tphi[ttt,:,:]
       tempeddv_CEM[ttt,:,:] = - Tp[ttt,:,:]
       dTdt_CEM[ttt,:,:] = temprmc_CEM[ttt,:,:] + tempedd_CEM[ttt,:,:]

       # (Seviour et al. 2012) zonal-mean forces due to waves drag, related to psi_TEM
       dummy,mmm = np.gradient(angmom[ttt,:,:],targetp1d,latrad,edge_order=2)
       wave_drag[ttt,:,:] = vstar[ttt,:,:]* mmm / (myp.a * acosphi2d)
     
     # (Seviour et al. 2012) transformed eulerian mean streamfunction
     w = np.isnan(vstar) # save NaN locations 
     vstar[w] = 0. # necessary otherwise integrations fail
     # integration loop
     x = targetp1d[:] # coordinate
     #x = np.insert(x,0,0) # JL: integrate from p=0 towards p
     x = np.append(x,0) # JL: integrate from p=0 towards p
     for ttt in range(nt):
       for yyy in range(nlat):
          y = vstar[ttt,:,yyy] # integrand
          #y = np.insert(y,0,y[0]) # JL: integrate from p=0 towards p
          y = np.append(y,y[-1]) # JL: integrate from p=0 towards p
       for zzz in range(0,nz):
#            the minus sign below comes from the fact that x is ordered by decreasing values of p
#            whereas the integral should be performed from 0 to p. 
          psim_TEM[ttt,zzz,yyy] = -scipy.integrate.simps(y[zzz:],x[zzz:])*cosphi2d[0,yyy]
#        psim[ttt,zzz,yyy] = scipy.integrate.simps(y[0:zzz+1],x[0:zzz+1])*alph[0,yyy]
# reset to NaN after integration
     vstar[w] = np.nan ; psim_TEM[w] = np.nan


 etape("EP flux",time0)


## pole problem
if nopole and not short:
  if extended:
      divFphi[:,:,0] = np.nan
      divFphi[:,:,-1] = np.nan
      vstar[:,:,0] = np.nan
      vstar[:,:,-1] = np.nan
      omegastar[:,:,0] = np.nan
      omegastar[:,:,-1] = np.nan
  effbeta_bt[:,:,0] = np.nan
  effbeta_bt[:,:,-1] = np.nan
  effbeta_bc[:,:,0] = np.nan
  effbeta_bc[:,:,-1] = np.nan
  psim[:,:,0] = np.nan
  psim[:,:,-1] = np.nan

####################################################
etape("creating the target file",time0)

f = nc.Dataset(outfile,'w',format='NETCDF3_CLASSIC')

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
etape("3D variables",time0)
addvar(outfile,nam4,'p',targetp3d)
addvar(outfile,nam4,'u',u)
addvar(outfile,nam4,vartemp,temp)
addvar(outfile,nam4,'angmom',angmom)
addvar(outfile,nam4,'wangmom',wangmom)
addvar(outfile,nam4,'superindex',superindex)
if not short:
  addvar(outfile,nam4,'amt_mmc_v',amt_mmc_v)
  addvar(outfile,nam4,'temp_mmc_v',temp_mmc_v)
  addvar(outfile,nam4,'tpot_mmc_v',tpot_mmc_v)
  addvar(outfile,nam4,'mpvp',mpvp)
  addvar(outfile,nam4,'vpup',vpup)
  addvar(outfile,nam4,'vptp',vptp)
  if is_omega:
      addvar(outfile,nam4,'opup',opup)
      addvar(outfile,nam4,'optp',optp)
      addvar(outfile,nam4,'amt_mmc_w',amt_mmc_w)
      addvar(outfile,nam4,'temp_mmc_w',temp_mmc_w)
      addvar(outfile,nam4,'tpot_mmc_w',tpot_mmc_w)
  if is_gwdparam:
      addvar(outfile,nam4,'east_gwstress',east_gwstress)
      addvar(outfile,nam4,'west_gwstress',west_gwstress)
  addvar(outfile,nam4,'eke',eke)
  addvar(outfile,nam4,'tpot',tpot)
  addvar(outfile,nam4,'N2',N2)
  addvar(outfile,nam4,'effbeta_bt',effbeta_bt)
  addvar(outfile,nam4,'effbeta_bc',effbeta_bc)
  addvar(outfile,nam4,'ushear',ushear)
  addvar(outfile,nam4,'psim',psim)
  addvar(outfile,nam4,'omegamean',omega)
  if extended:
      addvar(outfile,nam4,'psi',psi)
      addvar(outfile,nam4,'Fphi',Fphi)
      addvar(outfile,nam4,'divFphi',divFphi)
      addvar(outfile,nam4,'divFp',divFp)
      addvar(outfile,nam4,'vstar',vstar)
      addvar(outfile,nam4,'Fp',Fp)
      addvar(outfile,nam4,'Fphi_simp',Fphi_simp)
      addvar(outfile,nam4,'Fp_simp',Fp_simp)
      addvar(outfile,nam4,'Fp_simp_eq',Fp_simp_eq)
      addvar(outfile,nam4,'EtoM',EtoM)
      addvar(outfile,nam4,'omegastar',omegastar)
      #addvar(outfile,nam4,'ratio',ratio)
      # outputs for transformed Eulerian-mean formalism
      addvar(outfile,nam4,'accrmc_TEM',accrmc_TEM)
      addvar(outfile,nam4,'mass_accrmc_TEM',mass_accrmc_TEM)
      addvar(outfile,nam4,'accrmch_TEM',accrmch_TEM)
      addvar(outfile,nam4,'accrmcv_TEM',accrmcv_TEM)
      addvar(outfile,nam4,'accedd_TEM',accedd_TEM)
      addvar(outfile,nam4,'mass_accedd_TEM',mass_accedd_TEM)
      addvar(outfile,nam4,'acceddh_TEM',acceddh_TEM)
      addvar(outfile,nam4,'acceddv_TEM',acceddv_TEM)
      addvar(outfile,nam4,'accedd_TEM_simp',accedd_TEM_simp)
      addvar(outfile,nam4,'acceddh_TEM_simp',acceddh_TEM_simp)
      addvar(outfile,nam4,'acceddv_TEM_simp',acceddv_TEM_simp)
      addvar(outfile,nam4,'dudt_TEM',dudt_TEM)
      addvar(outfile,nam4,'tempedd_TEM',tempedd_TEM)
      addvar(outfile,nam4,'tempeddh_TEM',tempeddh_TEM)
      addvar(outfile,nam4,'tempeddv_TEM',tempeddv_TEM)
      addvar(outfile,nam4,'temprmc_TEM',temprmc_TEM)
      addvar(outfile,nam4,'temprmch_TEM',temprmch_TEM)
      addvar(outfile,nam4,'temprmcv_TEM',temprmcv_TEM)
      addvar(outfile,nam4,'dTdt_TEM',dTdt_TEM)
      addvar(outfile,nam4,'psim_TEM',psim_TEM)
      addvar(outfile,nam4,'wave_drag',wave_drag)
      # outputs for classical Eulerian-mean formalism
      addvar(outfile,nam4,'accrmc_CEM',accrmc_CEM)
      addvar(outfile,nam4,'accrmch_CEM',accrmch_CEM)
      addvar(outfile,nam4,'accrmcv_CEM',accrmcv_CEM)
      addvar(outfile,nam4,'accedd_CEM',accedd_CEM)
      addvar(outfile,nam4,'acceddh_CEM',acceddh_CEM)
      addvar(outfile,nam4,'acceddv_CEM',acceddv_CEM)
      addvar(outfile,nam4,'dudt_CEM',dudt_CEM)
      addvar(outfile,nam4,'temprmc_CEM',temprmc_CEM)
      addvar(outfile,nam4,'temprmch_CEM',temprmch_CEM)
      addvar(outfile,nam4,'temprmcv_CEM',temprmcv_CEM)
      addvar(outfile,nam4,'tempedd_CEM',tempedd_CEM)
      addvar(outfile,nam4,'tempeddh_CEM',tempeddh_CEM)
      addvar(outfile,nam4,'tempeddv_CEM',tempeddv_CEM)
      addvar(outfile,nam4,'dTdt_CEM',dTdt_CEM)
    


#####################################################
#if 0 == 1:
#print("... adding 2D variables !")
#namdim2d = (nam4[0],nam4[2],nam4[3])
#addvar(outfile,namdim2d,'ISR',ISR)
#addvar(outfile,namdim2d,'OLR',OLR)

etape("",time0)
