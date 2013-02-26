#!/usr/bin/env python

'''
convert7id
==========

Distill example from 7id MDA->NeXus file

This example demonstrates the proposed way to best support the NeXus
goal of providing a default plot when the data file is opened.

* group attributes describe the contents of relevance
  * this is more consistent with "say as we do, do as we say"
  * the NXdata group describes the default plot
* root level indicates which NXentry to show
* NXentry group shows which NXdata to show
* NXdata group shows which dataset to plot
* NXdata group describes what are the dependent axes
* Dependent axes can be different, with different shapes, 
  for the same image data, in different groups
* able to describe data with great complexity
* simple pattern to follow
* Can allow NXdata to use *any* HDF5 dataset
'''


########### SVN repository information ###################
# $Date$
# $Author$
# $Revision$
# $URL$
# $Id$
########### SVN repository information ###################


import datetime
import h5py
import os
import sys
import nxh5_lib


path = os.path.join('..', 'data', 'mda')
sourceFile = os.path.join(path, '7idc_0040.h5')
targetFile = os.path.join(path, '7idc_0040_example.h5')

fOld = h5py.File(sourceFile, "r")
fNew = h5py.File(targetFile, "w")

nxh5_lib.addAttributes(fNew,
                        file_name=targetFile,
                        file_time=str(datetime.datetime.now()),
                        creator=fOld.attrs.get('creator'),
                        HDF5_Version=h5py.version.hdf5_version,
                        h5py_version=h5py.version.version,
                        default_NXentry = 'scan_0040'
                       )

entry = nxh5_lib.makeGroup(fNew, 'scan_0040', 'NXentry', 
                           default_NXdata='readback_positions')

# metadata about the sscan record and MDA file
note = nxh5_lib.makeGroup(entry, 'MDA_file', 'NXnote')
for item in ('date_time', 'original_filename', 'scan_number', 'scan_rank'):
    nxh5_lib.makeDataset(note, item, data=fOld['/scan_0040/'+item])

# copy the sscan dimensions into NXcollection groups, dim1 = outer, dim3 = inner
for dim in ('dim1', 'dim2', 'dim3'):
    coll = nxh5_lib.makeGroup(entry, dim, 'NXcollection')
    datasets = ['P1', 'T00']
    if dim == 'dim3':
        datasets += ['D09', 'D17', 'D18', 'D20']
    for dsName in datasets:
        oldPath = '/scan_0040/%s/%s' % (dim, dsName)
        data = fOld[oldPath]
        if oldPath == '/scan_0040/dim1/P1':
            # make one repair to data length (planned v. acquired lengths)
            data = fOld[oldPath][:5]
        ds = nxh5_lib.makeDataset(coll, dsName, data=data)
        for item in (fOld[oldPath].attrs):
            ds.attrs[item] = fOld[oldPath].attrs[item]

# Now, all relevant data is stored in NXcollection groups: dim1, dim2, dim3
# as collected by the EPICS sscan record and stored in MDA files

# NXdata group with image using target positions
nxdata = nxh5_lib.makeGroup(entry, 'target_positions', 'NXdata',
                          signal='image',
                          axes=['x', 'y', 'z'],
                          x_indices=[1],
                          y_indices=[1, 2],
                          z_indices=[1, 2, 3],
                          )
nxh5_lib.makeLink(nxdata, fNew['/scan_0040/dim3/D09'], 'image')
nxh5_lib.makeLink(nxdata, fNew['/scan_0040/dim1/P1'], 'x')  # target motor position
nxh5_lib.makeLink(nxdata, fNew['/scan_0040/dim2/P1'], 'y')  # delay generator setting
nxh5_lib.makeLink(nxdata, fNew['/scan_0040/dim3/P1'], 'z')  # target motor positions, values change with each increment of dim1 and dim2

# NXdata group with image using readback positions
nxdata = nxh5_lib.makeGroup(entry, 'readback_positions', 'NXdata',
                          signal='image',
                          axes=['rbv_x', 'rbv_y', 'rbv_z'],
                          rbv_x_indices=[1, 2, 3],
                          rbv_y_indices=[1, 2, 3],
                          rbv_z_indices=[1, 2, 3],
                          )
nxh5_lib.makeLink(nxdata, fNew['/scan_0040/dim3/D09'], 'image')
nxh5_lib.makeLink(nxdata, fNew['/scan_0040/dim3/D18'], 'rbv_x')  # 3-D readbacks to dim1/P1
nxh5_lib.makeLink(nxdata, fNew['/scan_0040/dim3/D17'], 'rbv_y')  # 3-D readout of dim2/P1
nxh5_lib.makeLink(nxdata, fNew['/scan_0040/dim3/D20'], 'rbv_z')  # 3-D readbacks to dim3/P1

fNew.close()
fOld.close()
