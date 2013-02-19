.. report_2idd documentation master file, created by
   sphinx-quickstart on Thu Feb 14 10:28:27 2013.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to report_2idd's documentation!
=======================================

Many sectors of the APS use the EPICS *sscan* record from *synApps* to collect
their experimental data.  The *saveData* process runs to store the data into
files using the *MDA* format.

This support provides a tool to read those MDA files and, for 1-D and
2-D scans, write the scan into ASCII text files according to the expected
layout provided by a previous program (``yca scanSee_report``, a
Yorick-based support).

See the program documentation for details.

Contents:

.. toctree::
   :maxdepth: 2

   mda2idd_gui
   mda2idd_report
   mda2idd_summary


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

