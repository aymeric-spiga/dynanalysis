import numpy as np

## compute mean
## author AS + AC
def mean(field,axis=None):
        if field is None: return None
        else: 
           if type(field).__name__=='MaskedArray':
              field.set_fill_value(np.NaN)
              zout=np.ma.array(field).mean(axis=axis,dtype=np.float64)
              if axis is not None:
                 zout.set_fill_value(np.NaN)
                 return zout.filled()
              else:return zout
           elif (np.isnan(np.sum(field)) and (type(field).__name__ not in 'MaskedArray')):
              zout=np.ma.masked_invalid(field).mean(axis=axis,dtype=np.float64)
              if axis is not None:
                 zout.set_fill_value([np.NaN])
                 return zout.filled()
              else:return zout
           else: 
              return np.array(field).mean(axis=axis,dtype=np.float64)
