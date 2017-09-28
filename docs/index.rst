
mda2idd_report documentation
============================

Many sectors of the APS use the EPICS [#]_ *sscan* record [#]_ from *synApps* [#]_ to collect
their experimental data.  The *saveData* process [#]_ runs in an EPICS IOC to store 
the *sscan* record data into binary files using the *MDA* [#]_ format.

This support provides a tool to read those MDA files and, for 1-D and
2-D scans, write the scan into ASCII text files according to the expected
layout provided by a previous program (``yca scanSee_report``, support 
based on the open-source *yorick* software with extensions to communicate
with EPICS using Channel Access).
	
.. figure:: main.png
	:width: 80%
	:alt: main window view
	
	Main window showing full summary of selected MDA file
	
.. [#] *EPICS*: http://www.aps.anl.gov/epics/
.. [#] EPICS *sscan* record: http://www.aps.anl.gov/bcda/synApps/sscan/sscanRecord.html
.. [#] *synApps*: http://www.aps.anl.gov/bcda/synApps/index.php
.. [#] more information on the *saveData* process: http://www.aps.anl.gov/bcda/synApps/sscan/sscanDoc.html
.. [#] MDA format specification: http://www.aps.anl.gov/bcda/synApps/sscan/saveData_fileFormat.txt

---------------

Contents
========

.. toctree::
   :maxdepth: 2

   mda2idd_gui
   mda2idd_report
   mda2idd_summary

Web URL
=======

the previous documentation is still visible:

* tiny: http://tinyurl.com/bq9l5o7
* preview: http://preview.tinyurl.com/bq9l5o7
* full: https://subversion.xray.aps.anl.gov/bcdaext/mda2idd_report/src/docs/_build/html/index.html

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
