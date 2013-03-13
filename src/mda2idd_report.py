#!/usr/bin/env python

'''
Generate ASCII text files from MDA files for APS station 2-ID-D

Objectives
------------

* Replaces *yviewer*, ``asciiRpt.py`` and ``mdaRpt.py``
* Creates a GUI similar to that of ``asciiRpt.py`` (aka *yviewer*)

Different than the output from *mdaAscii*, this module
converts 1-D and 2-D scans stored in MDA files [#]_ into the
text file format produced by ``yca scanSee_report`` (a
Yorick-based support).

.. [#] MDA format specification: http://www.aps.anl.gov/bcda/synApps/sscan/saveData_fileFormat.txt


Main Methods
------------

* :func:`report()`:
  converts MDA file to 1 or more ASCII text files, based on the rank

* :func:`report_list()`:
  process a list of MDA files

* :func:`summaryMda()`:
  text summary of a single MDA file (name, rank, datetime, ...)
    
Internal (but interesting) Methods
----------------------------------

* :func:`report_1d()`:
  report 1-D MDA scan data in the format for APS station 2-ID-D
  (called by :func:`report()`)

* :func:`report_2d()`:
  report 2-D MDA scan data in the format for APS station 2-ID-D
  (called by :func:`report()`)

* :func:`columnsToText()`:
  convert a list of column lists into rows of text

Dependencies
------------

operating system
^^^^^^^^^^^^^^^^^^^

None.  This software was developed on a Windows 7 system and tested on 
various Linux distributions (Ubuntu, mint, and RHEL Linux) and on MacOSX.  
It was also tested on solaris but the performance was too poor on that 
specific system to advocate its continued use.

MDA file support
^^^^^^^^^^^^^^^^^^^^^^

This code requires the *mda* file format support library from APS synApps.  
Principally, two files support files are needed.
Download them and place them in the same directory with this project.

* https://subversion.xray.aps.anl.gov/synApps/utils/trunk/mdaPythonUtils/mda.py
* https://subversion.xray.aps.anl.gov/synApps/utils/trunk/mdaPythonUtils/f_xdrlib.py

In the same directory, there are also a pair of files (*setup.cfg* & *setup.py*) 
that can be used to install the mda support into the python site-packages directory.
Install them with these commands:

>>> svn co https://subversion.xray.aps.anl.gov/synApps/utils/trunk/mdaPythonUtils mdaPythonUtils
>>> cd mdaPythonUtils
>>> python setup.py install

---------------------------------

Source Code Documentation
-------------------------

'''


########### SVN repository information ###################
# $Date$
# $Author$
# $Revision$
# $URL$
# $Id$
########### SVN repository information ###################


import glob
import os
import optparse
import mda


ROW_INDEX_FORMAT = '%5d'

__description__ = "Generate ASCII text files from MDA files for APS station 2-ID-D"
__svnid__ = "$Id$"


def summaryMda(mdaFileName):
    '''
    text summary of a single MDA file (name, rank, datetime, ...)
    
    Developed for the GUI to give the user a preview of the file
    before saving its data as ASCII to a text file.
    '''
    if not os.path.exists(mdaFileName):
        return ''
    
    data = mda.readMDA(mdaFileName)
    if data is None:
        return 'could not read: ' + mdaFileName
    
    summary = []
    summary.append( 'MDA version = %.1f' % data[0]['version'] )
    summary.append( 'Filename = %s' % data[0]['filename'] )
    summary.append( 'rank = %d' % data[0]['rank'])
    summary.append( '1-D Scan # = %d' % data[0]['scan_number'] )
    if len(data) > 1:
        summary.append( '1-D scan timeStamp= %s' % data[1].time )
    summary.append( 'dimensions = %s' % str(data[0]['dimensions']))
    summary.append( 'acquired_dimensions = %s' % str(data[0]['acquired_dimensions']))
    summary.append('')
    summary.append( 'EPICS PVs')
    summary.append( '---------')
    summary.append('')
    for k in sorted(data[0].keys()):
        if k not in data[0]['ourKeys']:
            desc, unit, value, _, _ = data[0][k]
            txt = ""
            if len(desc) > 0:
                txt += " [%s]" % desc
            if len(unit) > 0:
                txt += " (%s)" % unit
            txt += " %s =" % k
            txt += " %s" % value
            summary.append(' '*4 + txt.strip())

    for dimNum in (1, 2, 3, 4):
        if len(data) > dimNum:
            summary.append('')
            summary.append( '%d-D Scan Info' % dimNum)
            summary.append( '-------------')
            base = data[dimNum]
            parts_dict = {
                'Positioners': base.p,
                'Detectors': base.d,
                'Triggers': base.t,
            }
            for partname, part in parts_dict.items():
                if len(part) > 0:
                    indent = ' '*4
                    summary.append('')
                    summary.append( indent + partname)
                    summary.append( indent + ('~'*len(partname)))
                    summary.append('')
                    for item in part:
                        if partname == 'Triggers':
                            txt = "%s = %s" % (item.name, str(item.command))
                        else:
                            txt = "%s:  %s" % (item.fieldName, item.name)
                            if len(unit) > 0:
                                txt += " (%s)" % unit
                            if len(item.desc) > 0:
                                txt += ": %s" % item.desc
                        summary.append( indent + txt )

    return '\n'.join(summary)


class ReadMdaException(Exception):
    '''MDA files are all version 1.3 (+/- 0.01)'''
    pass


class RankException(Exception):
    '''this report can only handle ranks 1 and 2'''
    pass


def report(mdaFileName, allowException=False):
    '''
    converts MDA file to 1 or more ASCII text files, based on the rank
    
    :param str mdaFileName: includes absolute or relative path to MDA file
    :returns dict: {mdaFileName: [asciiFileName]}
    '''
    converted = {}
    if not os.path.exists(mdaFileName):
        return converted

    asciiPath = getAsciiPath(mdaFileName)

    data = mda.readMDA(mdaFileName)
    if data is None:
        msg = "could not read data from MDA file: " + mdaFileName
        if allowException:
            raise ReadMdaException, msg
        else:
            print msg
        return converted
        
    rank = data[0]['rank']

    if rank in (1, 2):
        if len(data[0]['acquired_dimensions']) == rank:
            method = {1: report_1d, 2: report_2d}[rank]
            for key, value in method(data).items():
                writeOutput(asciiPath, key, value)
                if mdaFileName not in converted:
                    converted[mdaFileName] = []
                converted[mdaFileName].append( os.path.join(asciiPath, key) )
    else:
        msg = '%d-D data: not handled by this code' % rank
        if allowException:
            raise RankException, msg
        else:
            print msg
                
    return converted


def report_1d(data):
    '''
    report 1-D MDA scan data in this format:
    
    .. code-block:: guess
       :linenos:

       ; 
       ; ========================================================
       ; Filename: /home/2-iddf/data12c3/Alix_NWU/mda/2iddf_0001.mda
       ; 1D Scanno # =        1
       ; title= (Scan # 1)
       ; xtitle= PI_sample1_X(micron)
       ; ytitle= 
       ; timeStamp= OCT 30, 2012 12:03:41
       ; comment= 
       ; 
       ; 
       ; DIS:             P1                 D1                 D2                 ...
       ; Name:            2iddf:m38.VAL      S:SRcurrentAI      2idd:scaler1_cts1. ...
       ; Desc:            PI_sample1_X       SR Current                            ...
       ; Unit:            micron             mA                                    ...
         1               1197.47            122.374            169.800             ...
         2               1198.97            122.347            169.400             ...
         3               1200.47            122.318            171.000             ...
         4               1201.97            122.289            173.600             ...
         5               1203.47            122.777            169.000             ...

    '''
    header = [ ';', ]
    header.append( '; %s' % ('='*55) )
    header.append( '; Filename: %s' % data[0]['filename'] )
    header.append( '; 1D Scanno # = %8d' % data[0]['scan_number'] )
    header.append( '; title= (Scan # %d)' % data[0]['scan_number'] )
    header.append( '; xtitle= %s(%s)' % (data[1].p[0].desc, data[1].p[0].unit) )
    header.append( '; ytitle= ' )
    header.append( '; timeStamp= %s' % data[1].time.split('.')[0] )
    header.append( '; comment= ' )
    
    # build the table, one column at a time, then use zip to transpose the table to rows
    columns = []
    columns.append(
        ['; %-5s ' % (item+':') for item in ('DIS', 'Name', 'Desc', 'Unit')]
      + [ROW_INDEX_FORMAT % (rownum+1) for rownum in range(data[1].curr_pt)]
    )
    for part in (data[1].p, data[1].d):  # positioners, then detectors
        for item in part:
            columns.append(
                [item.fieldName, item.name, item.desc, item.unit]
              + [str(_) for _ in item.data]
            )
    
    # return value is a dictionary:
    #   key is file name, value is file contents
    return { getAsciiFileName(data): '\n'.join(header) + '\n' + columnsToText(columns)  }


def report_2d(data):
    '''
    report 2-D MDA scan data in this format, one file for each  detector:
    
    .. code-block:: guess
       :linenos:

       ; FILE:  /home/2-iddf/data12c3/Alix_NWU/mda/2iddf_0012.mda
       ; Title:  Image#16 (2iddf:mca1.R9) - D01
       ; Scan # =       12 ,  Detector # =       16 ,   col=       51 ,   row=       51
       ;            Yvalue:        -1712.03        -1711.53        -1711.03        -1710.53        ...
       ;             Yindex               1               2               3               4        ...
       ; Xindex,    Xvalue,        Image(I,J) Array                                                ...
         1          1289.55         0.00000         0.00000         0.00000         0.00000        ...
         2          1290.05         0.00000         0.00000         0.00000         0.00000        ...
         3          1290.55         0.00000         0.00000         0.00000         0.00000        ...

    '''
    scanNum = data[0]['scan_number']
    output = {}
    for detNum in range(data[2].nd):
        asciiFile = getAsciiFileName(data, detNum=detNum)

        num_cols = data[1].curr_pt
        num_rows = data[2].curr_pt

        header = [ '; FILE:  %s' % data[0]['filename'], ]
        header.append(  '; Title:  Image#%d (%s) - %s' % (detNum+1, data[2].d[detNum].name, data[2].d[detNum].fieldName) )
        header.append( '; Scan # = %8d ,  Detector # = %8d ,  col= %8d ,  row= %8d' % (scanNum, detNum+1, num_cols, num_rows ) )

        # build the table, one column at a time, then use zip to transpose the table to rows
        columns = []
        columns.append(
            [';', ';', '; Xindex,']
          + [ROW_INDEX_FORMAT % (rownum+1) for rownum in range(num_rows)]
          # TODO: right-pad when curr_pt < npts !
        )
        columns.append(
            ['Yvalue:', 'Yindex', 'Xvalue,']
          + [str(item) for item in data[2].p[0].data[0]]
          # TODO: right-pad when curr_pt < npts !
        )
        for colNum in range(num_cols):
            img_title = {False: 'Image(', True: ''}[colNum > 0]
            columns.append(
                [str(data[1].p[0].data[colNum]), str(colNum+1), img_title]
              + [str(item) for item in data[2].d[detNum].data[colNum]]
              # TODO: right-pad when curr_pt < npts !
            )

        output[asciiFile] = '\n'.join(header) + '\n' + columnsToText(columns) 
    
    # return value is a dictionary:
    #   keys are file names, values are file contents
    return output


def columnsToText(columns):
    '''
    convert a list of column lists into rows of text
    
    column widths will be chosen from the maximum character width of each column
    
    :param [[str]] columns: list of column lists (all same length)
    :returns str: text block, with line separators
    
    Example::
    
        >>> columns = [ ['1A', '2A'], ['1B is long', '2B'], ['1C', '2C'] ]
        >>> print columnsToText( columns )
        1A  1B is long  1C
        2A  2B          2C
    
    '''
    # get the largest width for each column
    widths = [max(map(len, item)) for item in columns]
    # left-align each column
    sep = ' '*2
    fmt = sep.join(['%%-%ds' % item for item in widths])
    # rows = zip(*columns) : matrix transpose
    result = [fmt % tuple(row) for row in zip(*columns)]
    return '\n'.join(result)


def writeOutput(path, filename, output):
    '''
    write the output text buffer to the file
    
    :param str path: absolute or relative path to directory 
                     where file should be written
    :param str filename: name of file to be written, existing file
                         will be overwritten without warning
    :param str output: text buffer to write to file
    '''
    if os.path.exists(path):
        f = open(os.path.join(path, filename), 'w')
        f.write(output)
        f.close()


def getAsciiFileName(data, detNum = None):
    '''
    return the proper text file name, based on the file name stored in the MDA data structure
    
    :param obj data: MDA data structure returned by mda.readMDA()
    :param int detNum: (2-D only)
    '''
    mdaFileName = os.path.basename(data[0]['filename'])
    root = os.path.splitext(mdaFileName)[0]
    sep = os.path.extsep
    rank = data[0]['rank'] 
    if rank == 1:
        asciiFileName = sep.join([root, '1d', 'txt'])
    if rank == 2:
        detector_channel = data[2].d[detNum].fieldName
        asciiFileName = sep.join([root, 'im'+detector_channel, 'txt'])
    return asciiFileName


def getAsciiPath(mdaFileName):
    '''
    given the path to the MDA file, return the related ASCII file path
    
    Create the path to the ASCII directory if it does not exist.
    If we cannot create the ASCII dir path, return the MDA file path instead.
    
    The default expectation is that the files are stored 
    in this type of directory structure::
    
      some/path/to/data/
        ./MDA/
           scan_0001.mda
        ./ASCII/
           scan_0001.1d.txt

    '''
    mdaPath = os.path.dirname(mdaFileName)
    asciiPath = os.path.join(mdaPath, '..', 'ASCII')
    if not os.path.exists(asciiPath):
        os.makedirs(asciiPath)
        if not os.path.exists(asciiPath):
            #raise OSError, "could not create ASCII subdirectory, does not exist either"
            asciiPath = mdaPath
    return asciiPath


def developer_test():
    '''only for use in code development and testing'''
    path = os.path.join('..', 'data', 'mda')
    if os.path.exists(path):
        os.chdir(path)
        for name in glob.glob('*.mda'):
            converted = report(name)
            # report what was converted to stdout
            for key, value in converted.items():
                print key, '-->', ', '.join(sorted(value))


def report_list(mdaFileList):
    '''process a list of MDA files'''
    for mdaFile in mdaFileList:
        report(mdaFile)


def main():
    '''handles command-line input'''
    usage = 'usage: %prog [options] mdaFile [mdaFile ...]'
    parser = optparse.OptionParser(description=__description__, usage=usage, version=__svnid__)
    options, args = parser.parse_args()
    report_list(args)


if __name__ == '__main__':
    #developer_test()
    main()
