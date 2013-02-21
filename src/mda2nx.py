#!/usr/bin/env python

'''
mda2nx
=========

Convert MDA file to NeXus
'''


########### SVN repository information ###################
# $Date$
# $Author$
# $Revision$
# $URL$
# $Id$
########### SVN repository information ###################


import mda
import datetime
import h5py
import os
import sys
import nxh5_lib


def process(mdaFile):
    if os.path.exists(mdaFile):
        nxFile = os.path.splitext(mdaFile)[0] + os.path.extsep + 'h5'
        data = mda.readMDA(mdaFile)
        scan_number = data[0]['scan_number']
        rank = data[0]['rank']

        f = nxh5_lib.makeFile(nxFile, file_name=nxFile,
                file_time=str(datetime.datetime.now()),
                creator="mda2nx.py",
                HDF5_Version=h5py.version.hdf5_version,
                h5py_version=h5py.version.version)
#        
        nxentry = nxh5_lib.makeGroup(f, 'scan_%04d' % scan_number, "NXentry")
        nxh5_lib.makeDataset(nxentry, 'scan_number', data=scan_number)
        nxh5_lib.makeDataset(nxentry, 'scan_rank', data=rank)
        nxh5_lib.makeDataset(nxentry, 'original_filename', data=data[0]['filename'])
        if rank > 0:
            nxh5_lib.makeDataset(nxentry, 'date_time', data=data[1].time)
            for order in range(rank):
                dim = data[order+1]
                nxcoll = nxh5_lib.makeGroup(nxentry, 'dim'+str(order+1), "NXcollection")
                for item in dim.p:
                    nxh5_lib.makeDataset(nxcoll, 
                                            makeSafeHdf5Name(item.fieldName), 
                                            sscan_part = 'positioner',
                                            data=item.data, 
                                            units=item.unit, 
                                            number=item.number,
                                            long_name=item.desc,
                                            readback_name=item.readback_name,
                                            readback_readback_desc=item.readback_desc,
                                            readback_unit=item.readback_unit,
                                            step_mode=item.step_mode,
                                            EPICS_PV=item.name)
                for item in dim.d:
                    nxh5_lib.makeDataset(nxcoll, 
                                            makeSafeHdf5Name(item.fieldName), 
                                            sscan_part = 'detector',
                                            data=item.data, 
                                            units=item.unit, 
                                            long_name=item.desc,
                                            EPICS_PV=item.name)
                for item in dim.t:
                    nxh5_lib.makeDataset(nxcoll, 
                                            makeSafeHdf5Name('T%02d' % item.number), 
                                            sscan_part = 'trigger',
                                            data=item.command, 
                                            number=item.number,
                                            EPICS_PV=item.name)
        
        nxdata = nxh5_lib.makeGroup(nxentry, 'data', "NXdata")
        # TODO: to be a valid NeXus file MUST have some data, synthesize if no data acquired
        for order in range(rank):
            dim = data[order+1]
            # TODO: construct hard links from dimension positioners and detectors to items here
            # MDA file offers no help selecting which
            # TODO: must make some kind of default choice: P1 and D01 for each dimension, 
            #default plot of highest dimension detector but chek shapes to get the positioners right.
        
        pvs = epics_pvs(data)
        if len(pvs) > 0:
            nxcollection = nxh5_lib.makeGroup(nxentry, 'EPICS_PVs', "NXcollection")
            for pv, v in pvs.items():
                nxh5_lib.makeDataset(nxcollection, 
                                   makeSafeHdf5Name(pv), 
                                   data=v['value'], 
                                   units=v['units'], 
                                   long_name=v['description'], 
                                   EPICS_type=v['EPICS_type'], 
                                   EPICS_PV=pv)
        
        f.close()


def makeSafeHdf5Name(proposed):
    '''return a name that is safe to use as an HDF5 object'''
    safe = proposed # TODO: must do something here
    return safe


def epics_pvs(data):
    pvs = {}
    for pv in data[0].keys():
        if pv not in data[0]['ourKeys']:
            desc, unit, value, eType, count = data[0][pv]
            epics_type = mda.EPICS_types(eType)
            pvs[pv] = {
                       'description': desc,
                       'units': unit,
                       'value': value,
                       'EPICS_type': epics_type,
                       'count': count,
                       }
    return pvs


def main(mdaFileList):
    '''do the work'''
    for item in mdaFileList:
        process(item)


if __name__ == '__main__':
    filename = os.path.join('..', 'data', 'mda', '7idc_0040.mda')
    sys.argv.append(filename)
#    sys.argv.append(os.path.join('..', 'data', 'mda', '2iddf_0012.mda'))
#    sys.argv.append(os.path.join('..', 'data', 'mda', '2iddf_0001.mda'))
    main(sys.argv[1:])
    
    # fix items in 7ID file
    filename = os.path.join('..', 'data', 'mda', '7idc_0040.h5')
    f = h5py.File(filename, "a")
    dim2_p1 = f['/scan_0040/dim2/P1']
    dim3_p1 = f['/scan_0040/dim3/P1']
    dim3_d09 = f['/scan_0040/dim3/D09']
    nxdata = f['/scan_0040/data']
    series = 2
    nxh5_lib.makeDataset(nxdata, 
                           makeSafeHdf5Name('image'), 
                           data=dim3_d09[series], 
                           units=dim3_d09.attrs.get('units'), 
                           long_name=dim3_d09.attrs.get('long_name'), 
                           signal=1,
                           )
    nxh5_lib.makeDataset(nxdata, 
                           makeSafeHdf5Name('x'), 
                           data=dim2_p1[series], 
                           units=dim2_p1.attrs.get('units'),
                           long_name=dim2_p1.attrs.get('long_name'), 
                           )
    nxh5_lib.makeDataset(nxdata, 
                           makeSafeHdf5Name('y'), 
                           data=dim3_p1[series], 
                           units=dim3_p1.attrs.get('units'),
                           long_name=dim3_p1.attrs.get('long_name'), 
                           )
    
    nxf = nxh5_lib.makeFile("example_7id.h5", 
                            file_name="example_7id.h5",
                            file_time=f.attrs.get('file_time'),
                            creator=f.attrs.get('creator'),
                            HDF5_Version=h5py.version.hdf5_version,
                            h5py_version=h5py.version.version,
                            original_filename = f['/scan_0040/original_filename'],
                            original_datetime = f['/scan_0040/date_time'],
                            )
    nxentry = nxh5_lib.makeGroup(nxf, 'entry', "NXentry")
    for series in range(len(dim2_p1)): 
        nxdata = nxh5_lib.makeGroup(nxentry, 'data%d' % (series+1), "NXdata")
        nxh5_lib.makeDataset(nxdata, 
                               makeSafeHdf5Name('image'), 
                               data=dim3_d09[series], 
                               units=dim3_d09.attrs.get('units'), 
                               long_name=dim3_d09.attrs.get('long_name'), 
                               signal=1,
                               )
        nxh5_lib.makeDataset(nxdata, 
                               makeSafeHdf5Name('x'), 
                               data=dim2_p1[series], 
                               units=dim2_p1.attrs.get('units'),
                               long_name=dim2_p1.attrs.get('long_name'), 
                               )
        nxh5_lib.makeDataset(nxdata, 
                               makeSafeHdf5Name('y'), 
                               data=dim3_p1[series], 
                               units=dim3_p1.attrs.get('units'),
                               long_name=dim3_p1.attrs.get('long_name'), 
                               )
    comment = '''
These datasets came from data collected at the APS using the EPICS sscan record.
The <x> dataset represents the positioner values for each row.
The <y> dataset represents the positioner values for each column, but the actual values change with each row.
The <image> dataset should be plotted against <x> and <y> values such that image( x[row], y[row[col]] ).
    '''.strip()
    nxnote = nxh5_lib.makeGroup(nxentry, 'comment', "NXnote")
    nxh5_lib.makeDataset(nxnote, makeSafeHdf5Name('comment'), data=comment)
    nxf.close()

    f.close()
