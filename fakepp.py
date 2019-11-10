#! /usr/bin/env python


# 5 times faster than ppclass

import xarray as xr
import time as timelib

### GLOBAL VARIABLES TO HARDWIRE DIMENSIONS
zonadim = "longitude"
meridim = "latitude"
altidim = "altitude"
timedim = "Time"

### ----------------
### XARRAY WRAPPER
### ----------------
### this uses xarray and mimics ppclass 
### to quickly make an existing script a standalone script
### that only requires xarray and not ppclass
### ----------------
### there is some hardcoding
### because we just aim at the codes to work
### when using this wrapper
### obviously in a complete xarray-like integration [TBD]
### we would do things in a more flexible way
### directly calling something like
### > xr.open_dataset(fileAP,decode_times=False)["u"].values
### > ds = xr.open_dataset(fileAP,decode_times=False)
### > ds.sel(dict(dalist),method="nearest")[self.var].mean(dalistm).values
### then plotting, slicing, etc.. à la xarray (even using mfdataset)
### which makes planetoplot basically obsolete
### ----------------
class pp():

    def __init__(self,\
            file=None,\
            var=None,\
            x=None,\
            y=None,\
            z=None,\
            t=None,\
            compute=None):
        self.file = file
        self.var = var
        self.x = x     
        self.y = y 
        self.z = z 
        self.t = t 
        self.compute = compute
        return

    def opends(self):
        return xr.open_dataset(self.file,decode_times=False)        

    def get(self):
        ### open dataset
        ds = self.opends()     
        ### prepare dictionary for reduction
        dalist = []
        dalistm = []
        if self.x is not None:
            if self.x in ["0,360","-180,180"]:
                dalistm.append( zonadim )
            else:
                dalist.append( (zonadim,int(self.x)) ) 
        if self.y is not None:
            dalist.append( (meridim,int(self.y)) ) 
        if self.z is not None:
            dalist.append( (altidim,int(self.z)) )
        if self.t is not None:
            dalist.append( (timedim,int(self.t)) ) 
        ### return field values with (if applicable) data reduction
        ### -- if list stays [] then nothing is done
        dsred = ds.sel(dict(dalist),method="nearest")[self.var]
        ### averaging or computing anomalies
        if self.compute is not None: 
            if "pert" in self.compute:
                if "_x" in self.compute:
                    print("compute anomaly")
                    mm = ds[self.var].mean(zonadim)
                    dsred = dsred - mm
        else:
            dsred = dsred.mean(dalistm)
        return dsred

    def getf(self):
        return self.get().values

    def getfd(self):
        ds = self.opends()
        x = ds.coords[zonadim]
        y = ds.coords[meridim]
        z = ds.coords[altidim]
        t = ds.coords[timedim]
        return self.get().values,x.values,y.values,z.values,t.values


#######################################
#fileAP="diagfi5.nc"
#charx="60"
#charx="0,360"
#time0 = timelib.time()
#u=pp(file=fileAP,var="u",x=charx,compute="pert_x").getf()
#print(u.shape)
#u=pp(file=fileAP,var="u",x=charx).getf()
#print(u.shape)
#u=pp(file=fileAP,var="u").getf()
#u=pp(file=fileAP,var="v").getf()
#print(u.shape)
#u,xdim,ydim,zdim,tdim=pp(file=fileAP,var="u",x=charx).getfd()
#print(timelib.time() - time0)
########################################




