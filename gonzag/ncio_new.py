#!/usr/bin/env python3
# -*- Mode: Python; coding: utf-8; indent-tabs-mode: nil; tab-width: 4 -*-

############################################################################
#
#       L. Brodeau, 2021
#
############################################################################

import numpy as nmp
from netCDF4 import Dataset, num2date, default_fillvals
from calendar import timegm
from datetime import datetime as dtm
from .config import ldebug

cabout_nc = 'Created with Gonzag package => https://github.com/brodeau/gonzag'


def GetTimeVector( ncfile ):
    '''
    # Get the time vector in the netCDF file and
    # returns it in 2 different interpretations:
    #  => vdate: time as a "strftime" type
    #  => itime: time as UNIX epoch time, aka "seconds since 1970-01-01 00:00:00" (integer)
    '''
    if ldebug: print(' *** reading and converting time vector into '+ncfile+' ...')
    id_f = Dataset(ncfile)
    list_var = id_f.variables.keys()
    for cv in [ 'time', 'time_counter', 'none' ]:
        if cv in list_var:
            clndr = id_f.variables[cv]
            vdate = num2date( clndr[:], clndr.units, clndr.calendar )
            break
    id_f.close()
    if cv == 'none': MsgExit('found no time-record variable in file '+ncfile)
    #
    # Create the Unix Epoch time version:
    Nt = len(vdate)
    itime = nmp.zeros(Nt, dtype=nmp.int64)
    cfrmt = '%Y-%m-%d %H:%M:%S'
    for jt in range(Nt): itime[jt] = timegm( dtm.strptime( vdate[jt].strftime(cfrmt) , cfrmt ).timetuple() )
    if ldebug: print('      => Done!\n')
    #
    return vdate, itime


def GetModelCoor( ncfile, what ):
    '''
    #   list_dim = list(id_f.dimensions.keys()) ;  print(" list dims:", list_dim)
    '''
    cv_coor_test = nmp.array([[ 'lat','latitude', 'nav_lat','gphit','LATITUDE', 'none' ],
                              [ 'lon','longitude','nav_lon','glamt','LONGITUDE','none' ]])
    if   what ==  'latitude': ii = 0
    elif what == 'longitude': ii = 1
    else: MsgExit(' "what" argument of "GetModelCoor()" only supports "latitude" and "longitude"')
    #
    id_f = Dataset(ncfile)
    list_var = list(id_f.variables.keys())
    for ncvar in cv_coor_test[ii,:]:
        if ncvar in list_var: break
    if ncvar == 'none': MsgExit('could not find '+what+' array into model file')
    #
    nb_dim = len(id_f.variables[ncvar].dimensions)
    if   nb_dim==1: MsgExit('FIX ME! Model '+what+' is 1D')
    elif nb_dim==2: xwhat = id_f.variables[ncvar][:,:]
    elif nb_dim==3: xwhat = id_f.variables[ncvar][0,:,:]
    else: MsgExit('FIX ME! Model '+what+' has a weird number of dimensions')
    id_f.close()
    print(' *** Model '+what+' var is: "'+ncvar+'" ! with '+str(nb_dim)+' dimensions!',nmp.shape(xwhat),'\n')
    #
    return xwhat


def GetModelLSM( ncfile, what ):
    '''
    # Returns the land-sea mask on the source/moded domain: "1" => ocean point, "0" => land point
    # => 2D array [integer]
    '''
    print('\n *** what we use to define model land-sea mask:\n    => "'+what+'" in "'+ncfile+'"\n')
    l_fill_val = (what[:10]=='_FillValue')
    ncvar = what
    if l_fill_val: ncvar = what[11:]
    #
    id_f = Dataset(ncfile)
    ndims = len(id_f.variables[ncvar].dimensions)
    if l_fill_val:
        # Mask is constructed out of variable and its missing value
        if ndims!=3: MsgExit(ncvar+' is expected to have 3 dimensions')
        xmsk = 1 - id_f.variables[ncvar][0,:,:].mask
    else:
        # Mask is read in mask file...
        if   ndims==2: xmsk = id_f.variables[ncvar][:,:]
        elif ndims==3: xmsk = id_f.variables[ncvar][0,:,:]
        elif ndims==4: xmsk = id_f.variables[ncvar][0,0,:,:]
        else: MsgExit('FIX ME! Mask '+ncvar+' has a weird number of dimensions:'+str(ndims))
    #
    id_f.close()
    return xmsk.astype(int)


def GetSatCoord( ncfile, it1, it2, what ):
    #
    cv_coor_test = nmp.array([[ 'lat','latitude', 'LATITUDE',  'none' ],
                              [ 'lon','longitude','LONGITUDE', 'none' ]])
    if   what ==  'latitude': ii = 0
    elif what == 'longitude': ii = 1
    else: MsgExit('"what" argument of "GetSatCoord()" only supports "latitude" and "longitude"')
    #
    id_f = Dataset(ncfile)
    list_var = list(id_f.variables.keys())
    for ncvar in cv_coor_test[ii,:]:
        if ncvar in list_var: break
    if ncvar == 'none': MsgExit('could not find '+what+' array into satellite file')
    #
    nb_dim = len(id_f.variables[ncvar].dimensions)
    if nb_dim==1: vwhat = id_f.variables[ncvar][it1:it2+1]
    else: MsgExit('FIX ME! Satellite '+what+' has a weird number of dimensions (we expect only 1: the time-record!)')
    id_f.close()
    print(' *** Satellite '+what+' var is: "'+ncvar+'", of size',nmp.shape(vwhat),'\n')
    #
    return vwhat


def Save2Dfield( ncfile, XFLD, xlon=[], xlat=[], name='field', unit='', long_name='', mask=[], clon='nav_lon', clat='nav_lat' ):
    #LOLO IMPROVE !
    (nj,ni) = nmp.shape(XFLD)
    f_o = Dataset(ncfile, 'w', format='NETCDF4')
    f_o.createDimension('y', nj)
    f_o.createDimension('x', ni)
    if (xlon != []) and (xlat != []):
        if (xlon.shape == (nj,ni)) and (xlon.shape == xlat.shape):
            id_lon  = f_o.createVariable(clon ,'f4',('y','x',), zlib=True, complevel=5)
            id_lat  = f_o.createVariable(clat ,'f4',('y','x',), zlib=True, complevel=5)
            id_lon[:,:] = xlon[:,:]
            id_lat[:,:] = xlat[:,:]
    id_fld  = f_o.createVariable(name ,'f4',('y','x',), zlib=True, complevel=5)
    if long_name != '': id_fld.long_name = long_name
    if unit      != '': id_fld.units     = unit
    if nmp.shape(mask) != (0,):
        xtmp = nmp.zeros((nj,ni))
        xtmp[:,:] = XFLD[:,:]
        idx_land = nmp.where( mask < 0.5)
        xtmp[idx_land] = nmp.nan
        id_fld[:,:] = xtmp[:,:]
        del xtmp
    else:
        id_fld[:,:] = XFLD[:,:]
    f_o.about = cabout_nc
    f_o.close()
    return


def SaveTimeSeries( ivt, xd, vvar, ncfile, time_units='unknown', vunits=[], vlnm=[], missing_val=-9999. ):
    '''
    #  * ivt: time vector (integer)
    #  *  xd: 2D numpy array that contains Nf time series of length Nt
    #        hence of shape (Nf,Nt)
    #  * vvar: 1D array of the variable names
    #  * vunits, vlnm: 1D arrays of the variable units and long names
    #  * missing_val: value for missing values...
    '''
    (Nf,Nt) = xd.shape
    if len(ivt) != Nt: MsgExit('SaveTimeSeries() => disagreement in the number of records between "ivt" and "xd"')
    if len(vvar)!= Nf: MsgExit('SaveTimeSeries() => disagreement in the number of fields between "vvar" and "xd"')
    l_f_units = (nmp.shape(vunits)==(Nf,)) ; l_f_lnm = (nmp.shape(vlnm)==(Nf,))
    #
    print('\n *** About to write file "'+ncfile+'"...')
    f_o = Dataset(ncfile, 'w', format='NETCDF4')
    f_o.createDimension('time', None)
    id_t = f_o.createVariable('time','f8',('time',))
    id_t.calendar = 'gregorian' ; id_t.units = time_units
    #
    id_d = []
    for jf in range(Nf):
        id_d.append( f_o.createVariable(vvar[jf],'f4',('time',), fill_value=missing_val, zlib=True, complevel=5) )
        if l_f_units: id_d[jf].units   = vunits[jf]
        if l_f_lnm:   id_d[jf].long_name = vlnm[jf]
    #
    print('   ==> writing "time"')
    id_t[:] = ivt.astype(nmp.float64)
    for jf in range(Nf):
        print('   ==> writing "'+vvar[jf]+'"')
        id_d[jf][:] = xd[jf,:]
    f_o.about = cabout_nc
    f_o.close()
    print(' *** "'+ncfile+'" successfully written!\n')
    return 0



class ModInput:
    '''
    # Get and build all the required arrays from the model data...
    '''
    def __init__( self, file_mod, name_ssh_mod, file_lsm_mod, name_lsm_mod, ew_prd_mod=-1 ):

        chck4f(file_mod)
        if name_lsm_mod=='_FillValue':
            clsm = name_lsm_mod+'@'+name_ssh_mod
        else:
            clsm = name_lsm_mod
            chck4f(file_lsm_mod)
        print('\n Model: '+file_mod+'\n')

        self.vdate, self.itime = GetTimeVector( file_mod )

        # Get model coordinates and land-sea mask:                                                                                                                          
        self.xlat = GetModelCoor( file_mod,  'latitude' )
        self.xlon = GetModelCoor( file_mod, 'longitude' )
        mask = GetModelLSM( file_lsm_mod, clsm ) ; # land-sea mask...                                                                                                     
        (Nj,Ni) = self.xlat.shape
        if self.xlon.shape != (Nj,Ni) or mask.shape != (Nj,Ni): MsgExit('shape disagreement for model arrays')
        self.xlon = nmp.mod(self.xlon, 360.) ; # forces longitude to be in the [0,360] range...                                                                                   
        #if ldebug: Save2Dfield( 'mask_model.nc', mask, name='mask' ) #lolodbg                                                                                            

        # Rough estimate of the resolution of the model grid:                                                                                                               
        res = GetModelResolution( self.xlon )
        if res>5. or res<0.001: MsgExit('Model resolution found is surprising, prefer to stop => check "GetModelResolution()" in utils.py')
        self.hres_deg = res
        
        # Global or regional config ?                                                                                                                                       
        l_glob_lon_wize, l360, lon_min, lon_max = IsGlobalLongitudeWise( xlon_m, resd=res_model_dg )
        lat_min = nmp.amin(xlat_m) ; lat_max = nmp.amax(xlat_m)
        cw = 'regional'
        if l_glob_lon_wize: cw = 'global'
        print('     => lat_min, lat_max = ', lat_min, lat_max)
        print('     => lon_min, lon_max = ', lon_min, lon_max, '\n')
        print(' *** Seems like the model domain is '+cw+' (in terms of longitude span)...')
        if ew_prd_mod>=0 and not l_glob_lon_wize:
            print('\n  WARNING: forcing East-West periodicity to NONE (ew_prd_mod=-1) because regional domain!\n')

        self.IsGlobal  = l_glob_lon_wize
        self.Is360     = l360
        self.LatRange  = ( lat_min, lat_max )
        self.LonRange  = ( lon_min, lon_max )
        
        
        
class SatInput:

    def __init__( self, file_sat, name_ssh_sat):

        chck4f(file_sat)
        print('\n Satellite: '+file_sat'\n')

        self.vdate, self.itime = GetTimeVector( file_sat )

        
