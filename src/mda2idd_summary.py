#!/usr/bin/env python

'''
Generate ASCII text summaries of MDA files for APS station 2-ID-D


---------------


Source Code Documentation
-------------------------

.. autosummary::

    ~summaryMda
    ~summary_list

--------------

'''


import optparse
import os
import mda


ROW_INDEX_FORMAT = '%5d'

__description__ = "Generate ASCII text summary of MDA files for APS station 2-ID-D"
__svnid__ = "$Id$"


def summaryMda(mdaFileName, shortReport = True):
    '''
    text summary of a single MDA file (name, rank, datetime, ...)
    
    Developed for the GUI to give the user a preview of the file
    before saving its data as ASCII to a text file.
    '''
    if not os.path.exists(mdaFileName):
        return ''
    
    if 'skimMDA' in mda.__dict__:
        reportType = {True: mda.skimMDA, False: mda.readMDA}[shortReport]
    else:
        reportType = mda.readMDA	# /APSshare/bin/python's mda does not have skimMDA
    try:
        data = reportType(mdaFileName) # just the header info
    except Exception as report:
        return "problem with %s: %s" % (mdaFileName, str(report))
    if data is None:
        return "could not read: " + mdaFileName
    
    headSection = data[0]
    summary = []
    summary.append( 'MDA version = %.1f' % headSection['version'] )
    summary.append( 'Filename = %s' % headSection['filename'] )
    summary.append( 'rank = %d' % headSection['rank'])
    summary.append( '1-D Scan # = %d' % headSection['scan_number'] )
    if len(data) > 1:
        summary.append( '1-D scan timeStamp= %s' % data[1].time )
    summary.append( 'dimensions = %s' % str(headSection['dimensions']))
    if 'acquired_dimensions' in headSection:
        summary.append( 'acquired_dimensions = %s' % str(headSection['acquired_dimensions']))
    summary.append('')
    
    # advanced header information obtainable through readMDA() method
    if 'ourKeys' in headSection:
        summary.append( 'EPICS PVs')
        summary.append( '---------')
        summary.append('')
        for k in sorted(headSection.keys()):
            if k not in headSection['ourKeys']:
                desc, unit, value, _, _ = headSection[k]
                txt = ""
                if len(desc) > 0:
                    txt += " [%s]" % desc
                if len(unit) > 0:
                    txt += " (%s)" % unit
                txt += " %s =" % k
                txt += " %s" % str(value)
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
                                txt = "%s   %s" % (item.fieldName, item.name)
                                if len(item.unit) > 0:
                                    txt += " (%s)" % item.unit
                                if len(item.desc) > 0:
                                    txt += ": %s" % item.desc
                            summary.append( indent + txt )

    return '\n'.join(summary)


def summary_list(mdaFileList):
    '''process a list of MDA files'''
    for mdaFile in mdaFileList:
        print "\n"+mdaFile
        print "="*len(mdaFile) + "\n"
        print summaryMda(mdaFile)


def main():
    '''handles command-line input'''
    usage = 'usage: %prog [options] mdaFile [mdaFile ...]'
    parser = optparse.OptionParser(description=__description__, usage=usage, version=__svnid__)
    options, args = parser.parse_args()
    summary_list(args)


if __name__ == '__main__':
#    import sys
#    sys.argv.append(os.path.join('..', 'data', 'mda', '2iddf_0009.mda'))
#    sys.argv.append(os.path.join('..', 'data', 'mda', '2iddf_0014.mda'))
    main()
