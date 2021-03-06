#!/usr/bin/env python

"""
GUI for :mod:`mda2idd_report`

Objectives
------------

Provide GUI tools to browse a file system and select
MDA files.  Process them with :mod:`mda2idd_report`.

Instructions
------------

Browse to a directory containing MDA files.
Select one.  A summary will be shown.
Choose:
* File --> Save  (or ^S)  to convert selected MDA file to an ASCII text file.
* File --> Convert entire Directory (^D) to convert all MDA files

For now, only `*.mda` files may be browsed.
ASCII text files will be written to directory: ../ASCII/
(relative to the MDA file directory)

Features
-----------

* presents file system list
* adds directory picker dialog and text entry box
* preview brief header or full summary of MDA file (^B)
* convert one selected MDA file to ASCII (^S)
* convert entire directory of MDA files to ASCII (^D)

---------------

Source Code Documentation
-------------------------

.. autosummary::

    ~MainWindow

--------------

"""


import optparse
import datetime
import glob
import platform
import os
import sys
import traceback
import wx
from xml.etree import ElementTree
from xml.dom import minidom
import mda2idd_report
import mda2idd_summary


__description__ = "GUI for mda2idd_report"
__version__ = "2016-04"
__author__ = "Pete Jemian"
__author_email__ = "jemian@anl.gov"
__url__ = "https://github.com/BCDA-APS/mda2idd_report"


RC_FILE = ".mda2idd_gui_rc.xml"


class MainWindow(wx.Frame):
    """
    Manage the application through the main window
    """
    
    def __init__(self, parent=None, start_fresh=False):
        wx.Frame.__init__(self, parent, wx.ID_ANY, u'mda2idd_gui', wx.DefaultPosition, 
                          wx.Size(200, 100), name=u'root', 
                          style=wx.DEFAULT_FRAME_STYLE)

        self.startup_complete = False
        self.selectedMdaFile = None
        self.preferences_file = self.GetDefaultPreferencesFileName()
        self.mrud = []      # most-recently-used directories
        
        self.getPreferences(start_fresh)
        
        self._init_menus()
        self._init_contents()
        
        # apply preferences
        self.SetSize(wx.Size(self.prefs['size_h'], self.prefs['size_v']))
        self.SetPosition(wx.Point(self.prefs['pos_h'], self.prefs['pos_v']))
        self.splitter1.SetSashPosition(self.prefs['sash_pos'], True)
        self.menu_file.Check(self.id_menu_report, self.prefs['short_summary'])

        self.update_mrud_menus()
        self.setStatusText('preferences file: ' + self.preferences_file)
        self.setSummaryText('')
        self.startup_complete = True
        
    def _init_menus(self):
        self.menu_file = wx.Menu(title='')
        item = self.menu_file.Append(text=u'&Save\tCtrl+S', id=wx.ID_ANY,
                              help=u'Save MDA data to ASCII text file')
        self.Bind(wx.EVT_MENU, self.OnMenuFileItemSave, id=item.GetId())

        item = self.menu_file.Append(
            text=u'Convert entire &Directory\tCtrl+D', 
            id=wx.ID_ANY,
            help=u'Convert all MDA files in current directory to ASCII text files')
        self.Bind(wx.EVT_MENU, self.OnConvertAll, id=item.GetId())
        
        self.menu_file.AppendSeparator()

        item = self.menu_file.AppendCheckItem(
            text=u'Brief &Report\tCtrl+R', 
            id=wx.ID_ANY,
            help=u'Show a brief summary report of the selected MDA file')
        self.Bind(wx.EVT_MENU, self.OnMenuFileItemReportStyle, id=item.GetId())
        self.id_menu_report = item.GetId()

        # TODO: provide a control to let user edit self.preferences_file
        # TODO: provide a control to let user edit self.prefs
        #self.menu_file.Append(text=u'&Preferences ...', id=id_menu_prefs,
        #                      help=u'Edit program preferences ...')
        #self.Bind(wx.EVT_MENU, self.OnMenuFileItemPrefs, id=id_menu_prefs)

        self.menu_file.AppendSeparator()

        
        item = self.menu_file.Append(text=u'MRUD list', id=wx.ID_ANY,
                              help=u'Most Recently Used Directories')
        self.menu_file.Enable(item.GetId(), False)
        self.mrud_insertion_pos = self.menu_file.GetMenuItemCount()

        self.menu_file.AppendSeparator()
        
        item = self.menu_file.Append(text=u'E&xit', id=wx.ID_ANY,
                              help=u'Quit this application')
        self.Bind(wx.EVT_MENU, self.OnMenuFileItemExit, id=item.GetId())

        self.menu_edit = wx.Menu(title='')

        self.menu_help = wx.Menu(title='')
        item = self.menu_help.Append(text=u'&About ...', id=wx.ID_ANY,
                              help=u'About this application')
        self.Bind(wx.EVT_MENU, self.OnAbout, id=item.GetId())

        self.menuBar1 = wx.MenuBar()
        self.menuBar1.Append(menu=self.menu_file, title=u'&File')
        self.menuBar1.Append(menu=self.menu_edit, title=u'&Edit')
        self.menuBar1.Append(menu=self.menu_help, title=u'&Help')
        self.SetMenuBar(self.menuBar1)
    
    def _init_contents(self):
        self.statusBar = self.CreateStatusBar()
        
        sizer = wx.BoxSizer(orient=wx.VERTICAL)

        self.dirPicker = wx.DirPickerCtrl (self, id=wx.ID_ANY, 
                       style=wx.DIRP_DIR_MUST_EXIST | wx.DIRP_USE_TEXTCTRL)
        sizer.Add(
                self.dirPicker,
                0,           # make vertically unstretchable
                wx.EXPAND |  # make horizontally stretchable
                wx.ALL,      # and make border all around
                )
        
        self.splitter1 = wx.SplitterWindow(self, id=wx.ID_ANY, style=wx.SP_3D)
        sizer.Add(
                self.splitter1,
                1,           # make vertically stretchable
                wx.EXPAND |  # make horizontally stretchable
                wx.ALL,      # and make border all around
                )
        
        self.textCtrl1 = wx.TextCtrl (self.splitter1, id=wx.ID_ANY, 
                                      style=wx.TE_READONLY|wx.TE_MULTILINE)
        self.setSummaryText('(empty)')

        self.dir = wx.GenericDirCtrl(self.splitter1, wx.ID_ANY, 
                                     dir=self.prefs['start_dir'],
                                     filter=self.prefs['file_filter'],
                                     )

        # Select the starting folder and expand to it
        self.setCurrentDirectory(self.prefs['start_dir'])
        self.splitter1.SplitVertically(self.dir, self.textCtrl1)
        
        tree = self.dir.GetTreeCtrl()

        wx.EVT_TREE_SEL_CHANGED(self, tree.GetId(), self.OnSelectTreeCtrlItem)
        wx.EVT_SPLITTER_SASH_POS_CHANGED(self, self.splitter1.GetId(), self.OnSashMoved)
        #self.Bind(wx.EVT_SIZE, self.OnWindowGeometryChanged)
        self.Bind(wx.EVT_MOVE, self.OnWindowGeometryChanged)
        self.Bind(wx.EVT_DIRPICKER_CHANGED, self.OnSelectDirPicker)

        self.SetSizerAndFit(sizer)
        
    def GetDefaultPreferencesFileName(self):
        '''
        return the name of the preferences file for this session
        
        The preferences file, an XML file that contains recent program
        settings for specific program features, is saved in the HOME
        (or USERPROFILE on Windows) directory for the user account under
        the ``.mda2idd_gui_rc.xml`` file name.  Here is an example
        from a Windows 7 system::

            <?xml version="1.0" encoding="UTF-8"?>
            <mda2idd_gui datetime="2013-03-06 13:09:17.593000" version="2013-02">
              <preferences_file>C:\Users\Pete\.mda2idd_gui_rc.xml</preferences_file>
              <written_by program="C:\Users\Pete\Documents\eclipse\mda2idd_report\src\mda2idd_gui.py"/>
              <subversion id="$Id$"/>
              <window>
                <size h="1212" v="561"/>
                <position h="114" v="232"/>
                <sash pos="300"/>
              </window>
              <file_filter>*.mda</file_filter>
              <starting_directory>C:\Users\Pete\Documents\eclipse\mda2idd_report\data\mda</starting_directory>
              <short_summary>False</short_summary>
              <mrud max_directories="9">
                <!--MRUD: Most-Recently-Used Directory-->
                <dir>C:\Users\Pete\Documents\eclipse\mda2idd_report\data\mda</dir>
                <dir>C:\Users\Pete\Apps\epics\synAppsSVN\support\sscan\documentation</dir>
                <dir>C:\Temp\mdalib</dir>
                <dir>C:\Users\Pete\Desktop\scanSee3.1\DATA</dir>
                <dir>C:\Users\Pete\Documents\eclipse\dc2mda\src</dir>
                <dir>C:\Users\Pete\Documents\eclipse\dc2mda\src\topo</dir>
              </mrud>
            </mda2idd_gui>
        
        Items remembered between program sessions include:
        
        * window size and position
        * position of the sash thats plits the file list from the summary output
        * the list of most-recently-used directories (MRUD)
        * the first directory to show (the last directory from which an MDA file was selected)
        
        .. note::  If more than one copy of this program is run by the same
           user at the same time, the content of the preferences file will
           be that of the latest action that forced an update to the file content.
        
        '''
        known_os = {
                'Windows': 'USERPROFILE', 
                'Linux': 'HOME',
                'SunOS': 'HOME',
                'Darwin': 'HOME',
              }
        this_os = platform.system()
        if this_os not in known_os.keys():
            raise Exception, "Unknown OS, cannot identify preferences"
        key = known_os[this_os]
        prefs_dir = os.environ[key]
        prefs_file = os.path.join(prefs_dir, RC_FILE)
        return prefs_file
        
    def OnSashMoved(self, event):
        '''user moved the sash'''
        self.prefs['sash_pos'] = self.splitter1.GetSashPosition()
        self.writePreferences()
        
    def OnWindowGeometryChanged(self, event):
        '''user changed the window size or position'''
        self.writePreferences()
        
    def OnSelectTreeCtrlItem(self, event):
        '''user selected something in the directory list tree control'''
        if not isinstance(event, wx.Event):
            self.setStatusText( "Not an event: %s" % str(event) )
            event.Skip()
            return
        selectedItem = self.dir.GetPath()
        self.setStatusText( 'selected: ' + selectedItem )
        if os.path.exists(selectedItem):
            if os.path.isfile(selectedItem):
                checked = self.menu_file.IsChecked(self.id_menu_report)
                summary = mda2idd_summary.summaryMda(selectedItem, checked)
                self.setSummaryText(summary)
                self.selectedMdaFile = selectedItem
                self.update_mrud(os.path.dirname(selectedItem))
                path = os.path.dirname(selectedItem)
                if path != self.prefs['start_dir']:
                    self.prefs['start_dir'] = path
                    self.update_mrud(path)
                    self.dirPicker.SetPath( path )
            if os.path.isdir(selectedItem):
                # must select a valid MDA file to join the MRUD list!
                #self.prefs['start_dir'] = selectedItem
                #self.update_mrud(selectedItem)
                self.dirPicker.SetPath( selectedItem )
            self.writePreferences()
    
    def OnSelectDirPicker(self, event):
        '''user changed the text or browsed to a directory in the picker'''
        if not isinstance(event, wx.Event):
            self.setStatusText( "Not an event: %s" % str(event) )
            event.Skip()
            return
        selectedItem = self.dirPicker.GetPath()
        if os.path.exists(selectedItem):
            if os.path.isdir(selectedItem):
                self.prefs['start_dir'] = selectedItem
                self.update_mrud(selectedItem)
                self.dir.ExpandPath(selectedItem)

    def OnMenuFileItemSave(self, event):
        '''save the selected MDA file as ASCII'''
        if self.selectedMdaFile is not None and os.path.exists(self.selectedMdaFile):
            self.setStatusText("converting MDA file %s to ASCII text" % self.selectedMdaFile)
            converted = mda2idd_report.report(self.selectedMdaFile)
            if self.selectedMdaFile in converted:
                msg = "converted MDA file " + self.selectedMdaFile
                num = len(converted[self.selectedMdaFile])
                msg += " to %d ASCII text file" % num
                if num > 1:
                    msg += "s"  # plural
                self.setStatusText(msg)
            else:
                self.setStatusText("No ASCII files written from " + self.selectedMdaFile)
    
    def OnMenuFileItemPrefs(self, event):
        '''save the preferences to a file'''
        # TODO: edit preferences dialog
        self.writePreferences()     # TODO: allow user to change file name?
    
    def OnMenuFileItemReportStyle(self, event):
        if self.selectedMdaFile is not None and os.path.exists(self.selectedMdaFile):
            checked = self.menu_file.IsChecked(self.id_menu_report)
            summary = mda2idd_summary.summaryMda(self.selectedMdaFile, checked)
            self.setSummaryText(summary)

    def OnMenuFileItemExit(self, event):
        '''
        User requested to quit the application
        
        :param event: wxPython event object
        '''
        # TODO: does not get here in RHEL5
        self.writePreferences()
        self.Close()
    
    def setCurrentDirectory(self, directory):
        '''set the current directory'''
        self.dir.ExpandPath(directory)
        self.dirPicker.SetPath(directory)
    
    def setSummaryText(self, text):
        '''post new text to the summary TextCtrl, clearing any existing text'''
        self.textCtrl1.ChangeValue(str(text))
    
    def appendSummaryText(self, text):
        '''post new text to the summary TextCtrl, appending to any existing text'''
        self.textCtrl1.AppendText(str(text))
        # FIXME: self.textCtrl1.Refresh()
        # Refresh() won't work here since the caller does not let the window get redrawn
        # Refactor to update as loop through MDA files progresses.
    
    def setStatusText(self, text):
        '''post new text to the status bar'''
        self.statusBar.SetStatusText(text)

    def getPreferences(self, start_fresh=False):
        '''
        set program preferences: default (start_fresh) 
        and then optionally override from a file
        '''
        self.prefs = {
            # define default prefs here as a dictionary
            'size_h': 700,
            'size_v': 320,
            'pos_h': 80,
            'pos_v': 20,
			'sash_pos': 200,
            'start_dir': os.path.dirname(self.preferences_file),
            'short_summary': True,
            'file_filter': '*.mda',
            'mrud': [
                     os.path.dirname(self.preferences_file),
                     ],
            'mrud_max_directories': 9,
        }
        if not start_fresh and os.path.exists(self.preferences_file):
            self.readPreferences()

    def readPreferences(self):
        '''read program prefs from a file'''
        if self.preferences_file is None:
            return

        if not os.path.exists(self.preferences_file):
            return
    
        tree = ElementTree.parse(self.preferences_file)
        root = tree.getroot()
        
        window = root.find('window')
        node = window.find('size')
        self.prefs['size_h'] = int(node.attrib['h'])
        self.prefs['size_v'] = int(node.attrib['v'])
        node = window.find('position')
        self.prefs['pos_h'] = int(node.attrib['h'])
        self.prefs['pos_v'] = int(node.attrib['v'])
        node = window.find('sash')
        self.prefs['sash_pos'] = int(node.attrib['pos'])

        node = root.find('mrud')
        if node is not None:
            self.prefs['mrud_max_directories'] = int(node.attrib['max_directories'])
            self.mrud = [subnode.text.strip() for subnode in node.findall('dir')]
        
        self.prefs['file_filter'] = root.find('file_filter').text.strip()
        node = root.find('short_summary')
        self.prefs['short_summary'] = node is None or 'true' == node.text.strip().lower()
        self.prefs['start_dir'] = root.find('starting_directory').text.strip()

    def writePreferences(self):
        '''save program prefs to a file'''
        if self.preferences_file is None:
            return
        
        if not os.path.exists(os.path.dirname(self.preferences_file)):
            return
        
        if not self.startup_complete:
            return

        self.prefs['size_h'], self.prefs['size_v'] = self.GetSize()
        self.prefs['pos_h'],  self.prefs['pos_v']  = self.GetPosition()
        self.prefs['short_summary'] = self.menu_file.IsChecked(self.id_menu_report)
    
        root = ElementTree.Element("mda2idd_gui")
        root.set("version", __version__)
        root.set("datetime", str(datetime.datetime.now()))
        
        node = ElementTree.SubElement(root, "preferences_file")
        node.text = self.preferences_file
        
        node = ElementTree.SubElement(root, "written_by")
        node.set("program", sys.argv[0])
        
        window = ElementTree.SubElement(root, "window")
        node = ElementTree.SubElement(window, "size")
        node.set("h", str(self.prefs['size_h']))
        node.set("v", str(self.prefs['size_v']))
        node = ElementTree.SubElement(window, "position")
        node.set("h", str(self.prefs['pos_h']))
        node.set("v", str(self.prefs['pos_v']))
        node = ElementTree.SubElement(window, "sash")
        node.set("pos", str(self.prefs['sash_pos']))
        
        node = ElementTree.SubElement(root, "file_filter")
        node.text = self.prefs['file_filter']
        
        node = ElementTree.SubElement(root, "starting_directory")
        node.text = self.prefs['start_dir']
        
        node = ElementTree.SubElement(root, "short_summary")
        node.text = str(self.prefs['short_summary'])
        
        mrud = ElementTree.SubElement(root, "mrud")
        mrud.append(ElementTree.Comment('MRUD: Most-Recently-Used Directory'))
        mrud.set("max_directories", str(self.prefs['mrud_max_directories']))
        for item in self.mrud:
            ElementTree.SubElement(mrud, "dir").text = item

        doc = minidom.parseString(ElementTree.tostring(root))
        xmlText = doc.toprettyxml(indent = "  ", encoding='UTF-8')
        
        f = open(self.preferences_file, 'w')
        f.write(xmlText)
        f.close()
    
    def update_mrud(self, newdir):
        '''MRUD: list of most-recently-used directories'''
        if newdir in self.mrud:
            if self.mrud[0] == newdir:
                return
            self.mrud.remove(newdir)
        fileList = self.listMdaFiles(newdir)
        if len(fileList) == 0:
            # no MDA files here, do not add this dir to MRUD list
            return
        self.mrud.insert(0, newdir)
        if len(self.mrud) >= self.prefs['mrud_max_directories']:
            self.mrud = self.mrud[:self.prefs['mrud_max_directories']]
        
        self.update_mrud_menus()
    
    def update_mrud_menus(self):
        '''manage the MRUD menu items'''
        
        if len(self.mrud) == 0:
            return
        
        # remove old MRUD items
        # look for items just after "MRUD list" until the separator
        item = self.menu_file.FindItemByPosition(self.mrud_insertion_pos)
        while item.GetKind() != wx.ITEM_SEPARATOR:
            #label = item.GetLabel()
            self.menu_file.Delete(item.GetId())
            item = self.menu_file.FindItemByPosition(self.mrud_insertion_pos)

        # add new MRUD items
        counter = 0
        for path in self.mrud:
            if os.path.exists(path):
                text = '%s\tCtrl+%d' % (path, counter+1)
                position = self.mrud_insertion_pos + counter
                item = self.menu_file.Insert(position, wx.ID_ANY, text=text)
                self.Bind(wx.EVT_MENU, self.OnMrudItem, id=item.GetId())
                counter += 1
        
    def OnMrudItem(self, event):
        '''handle MRUD menu items'''
        label = self.menu_file.GetLabelText(event.GetId())
        self.setCurrentDirectory(label)
        
    def OnAbout(self, event):
        '''show the "About" box'''
        # derived from http://wiki.wxpython.org/Using%20wxPython%20Demo%20Code
        # First we create and fill the info object
        info = wx.AboutDialogInfo()
        info.SetName( os.path.basename(sys.argv[0]) )
        info.SetVersion( __version__ )
        info.SetDescription( sys.argv[0] + '\n\n' + __doc__ )
        info.SetWebSite( __url__ )
        info.SetDevelopers(
          (
              'main author: ' + __author__ +  " <" + __author_email__ + ">",
              'MDA file support: Tim Mooney <mooney@aps.anl.gov>',
              __version__,
          )
        )
        wx.AboutBox(info)

    def OnConvertAll(self, event):
        '''selected the "ConvertAll" menu item'''
        # use path from preferences
        path = self.prefs['start_dir']
        # use path from self.dirPicker widget
        #path = self.dirPicker.GetPath()
        self.setStatusText('Converting all MDA files to ASCII in directory: ' + path)
        self.convertMdaDir(path)
        
    def convertMdaDir(self, path):
        '''convert all MDA files in a given directory'''
        fileList = self.listMdaFiles(path)
        if len(fileList) == 0:
            self.setSummaryText('No MDA files to convert in directory: ' + path)
            return
        self.setSummaryText('Converting these files:\n')
        known_exceptions = (
            mda2idd_report.ReadMdaException,    # some problem reading the MDA file
            mda2idd_report.RankException,       # only handle 1-D and 2-D scans
            IndexError,                         # requested array index is not available
            OSError,                            # 1 case: could not create ../ASCII directory
            Exception,                          # anything at all
        )
        for mdaFile in sorted(fileList):
            try:
                msg = ''
                answer = mda2idd_report.report(mdaFile, allowException=True)
                for k, v in answer.items():
                    msg += '\n* ' + k + ' --> '  # + str(v)
                    msg += "\n  " + "\n  ".join(v)
            except known_exceptions as answer:
                problem = mdaFile + '\n' + traceback.format_exc()
                # self.messageDialog('problem', problem)
                # return
                msg += '\n* ' + problem
            self.appendSummaryText(msg)
    
    def listMdaFiles(self, path):
        '''return a list of all MDA files in the path directory'''
        if not os.path.exists(path):
            self.setSummaryText('non-existent path: ' + path)
            return None
        # assumes self.prefs['file_filter'] is just '*.mda'
        return glob.glob(os.path.join(path, self.prefs['file_filter']))
        
    def messageDialog(self, description, text):
        '''
        Present a dialog asking user to acknowledge something

        :param str description: short description of message
        :param str text: message to be shown
        :param bool yes_and_no: if False (default), does not show a <No> button
        '''
        # confirm this step
        self.SetStatusText('Request Acknowledgment')
        dlg = wx.MessageDialog(self, text, description, wx.CANCEL)
        result = dlg.ShowModal()
        dlg.Destroy()           # destroy first
        return result


def main():
    '''presents the GUI'''
    parser = optparse.OptionParser(description=__description__)
    parser.add_option('-f', '--fresh', action='store_true', default=False,
                        dest='start_fresh',
                        help='start fresh (ignore / replace the prefs file)')
    parser.add_option('-v', '--version', action='version')
    # also: -h gets a help / usage message
    options = parser.parse_args()[0]  # ignore any args
    fresh_start = options.start_fresh

    app = wx.App()
    win = MainWindow(None, fresh_start)
    win.Show()
    app.MainLoop()


if __name__ == '__main__':
    main()
