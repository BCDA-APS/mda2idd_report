#!/usr/bin/env python

'''
GUI for mda2idd_report

Objectives
------------

Provide GUI tools to browse a file system and select
MDA files.  Process them with :mod:`report_2idd`.

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
* preview brief header or full summary of MDA file
* convert one selected MDA file to ASCII
* convert entire directory of MDA files to ASCII
'''


########### SVN repository information ###################
# $Date$
# $Author$
# $Revision$
# $URL$
# $Id$
########### SVN repository information ###################


import optparse
import datetime
import glob
import platform
import os
import sys
import wx
from xml.etree import ElementTree
from xml.dom import minidom
import mda2idd_report
import mda2idd_summary


__description__ = "GUI for mda2idd_report"
__version__ = "2013-02"
__svnid__ = "$Id$"
__author__ = "Pete Jemian"
__author_email__ = "jemian@anl.gov"
__url__ = "https://subversion.xray.aps.anl.gov/bcdaext/yviewer/"
__url__ = "$URL$".strip('$').split()[1]


RC_FILE = ".mda2idd_gui_rc.xml"


class MainWindow(wx.Frame):
    
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
        #print "menu item: ", item.GetId(), item.GetLabel()

        item = self.menu_file.Append(
            text=u'Convert entire &Directory\tCtrl+D', 
            id=wx.ID_ANY,
            help=u'Convert all MDA files in current directory to ASCII text files')
        self.Bind(wx.EVT_MENU, self.OnConvertAll, id=item.GetId())
        #print "menu item: ", item.GetId(), item.GetLabel()
        
        self.menu_file.AppendSeparator()

        item = self.menu_file.AppendCheckItem(
            text=u'Brief &Report\tCtrl+R', 
            id=wx.ID_ANY,
            help=u'Show a brief summary report of the selected MDA file')
        self.Bind(wx.EVT_MENU, self.OnMenuFileItemReportStyle, id=item.GetId())
        self.id_menu_report = item.GetId()
        #print "menu item: ", item.GetId(), item.GetLabel()

        # TODO: provide a control to let user edit self.preferences_file
        # TODO: provide a control to let user edit self.prefs
#        self.menu_file.Append(text=u'&Preferences ...', id=id_menu_prefs,
#                              help=u'Edit program preferences ...')
#        self.Bind(wx.EVT_MENU, self.OnMenuFileItemPrefs, id=id_menu_prefs)

        self.menu_file.AppendSeparator()

        
        item = self.menu_file.Append(text=u'MRUD list', id=wx.ID_ANY,
                              help=u'Most Recently Used Directories')
        self.menu_file.Enable(item.GetId(), False)
        self.mrud_insertion_pos = self.menu_file.GetMenuItemCount()
        #print "menu item: ", item.GetId(), item.GetLabel()

        self.menu_file.AppendSeparator()
        
        item = self.menu_file.Append(text=u'E&xit', id=wx.ID_ANY,
                              help=u'Quit this application')
        self.Bind(wx.EVT_MENU, self.OnMenuFileItemExit, id=item.GetId())
        #print "menu item: ", item.GetId(), item.GetLabel()

        self.menu_edit = wx.Menu(title='')

        self.menu_help = wx.Menu(title='')
        item = self.menu_help.Append(text=u'&About ...', id=wx.ID_ANY,
                              help=u'About this application')
        self.Bind(wx.EVT_MENU, self.OnAbout, id=item.GetId())
        #print "menu item: ", item.GetId(), item.GetLabel()

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
        '''return the name of the preferences file for this session'''
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
            mda2idd_report.report(self.selectedMdaFile)
    
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
        #print "set directory:", str(directory)
        self.dir.ExpandPath(directory)
        self.dirPicker.SetPath(directory)
    
    def setSummaryText(self, text):
        '''post new text to the summary TextCtrl, clearing any existing text'''
        #print "new summary:", str(text)
        self.textCtrl1.ChangeValue(str(text))
    
    def appendSummaryText(self, text):
        '''post new text to the summary TextCtrl, appending to any existing text'''
        #print "additional summary:", str(text)
        self.textCtrl1.AppendText(str(text))
    
    def setStatusText(self, text):
        '''post new text to the status bar'''
        #print "new status:", str(text)
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
        
        node = ElementTree.SubElement(root, "subversion")
        node.set("id", __svnid__)
        
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
                #print "menu item: ", item.GetId(), item.GetLabel()
                counter += 1
        
    def OnMrudItem(self, event):
        '''handle MRUD menu items'''
        label = self.menu_file.GetLabelText(event.GetId())
        #print "onMrudItem: ", event.GetId(), str(label)
        self.setCurrentDirectory(label)
#        self.setStatusText(label)
        
    def OnAbout(self, event):
        '''show the "About" box'''
        # derived from http://wiki.wxpython.org/Using%20wxPython%20Demo%20Code
        # First we create and fill the info object
        info = wx.AboutDialogInfo()
        info.SetName( sys.argv[0] )
        info.SetVersion( __version__ ) 
        info.SetDescription( __doc__ )
        if float(wx.VERSION_STRING[0:3]) < 2.9:	# pre-phoenix wxPython support
            info.SetWebSite( __url__ )
        else:						# phoenix wxPython support
            info.SetWebSite( __url__, desc=__svnid__ )
        author = __author__ +  " <" + __author_email__ + ">"
        info.SetDevelopers(
          (
              'main author: ' + __author__ +  " <" + __author_email__ + ">",
              'MDA file support: Tim Mooney <mooney@aps.anl.gov>'
          )
        )
        # Then we call wx.AboutBox giving it the info object
        wx.AboutBox(info)
        
    def OnConvertAll(self, event):
        '''selected the "ConvertAll" menu item'''
        # use path from preferences
        path = self.prefs['start_dir']
        # use path from self.dirPicker widget
        #path = self.dirPicker.GetPath()
	#print "convert directory:", path
        self.setStatusText('Converting all MDA files to ASCII in directory: ' + path)
        self.convertMdaDir(path)
        
    def convertMdaDir(self, path):
        '''convert all MDA files in a given directory'''
        if not os.path.exists(path):
            self.setSummaryText('non-existent path: ' + path)
            return
        # assumes self.prefs['file_filter'] is just '*.mda'
	fileList = glob.glob(os.path.join(path, self.prefs['file_filter']))
        if len(fileList) == 0:
            self.setSummaryText('No MDA files to convert in directory: ' + path)
            return
        self.setSummaryText('Converting these files:\n')
        for mdaFile in sorted(fileList):
            try:
                answer = mda2idd_report.report(mdaFile, allowException=True)
                msg = ''
                for k, v in answer.items():
                    msg += '\n* ' + k + ' --> ' + str(v)
            except (mda2idd_report.ReadMdaException, mda2idd_report.RankException), answer:
                msg = '\n* ' + mdaFile + ': ' + str(answer)
            self.appendSummaryText(msg)


def main():
    '''presents the GUI'''
    parser = optparse.OptionParser(description=__description__)
    parser.add_option('-f', '--fresh', action='store_true', default=False,
                        dest='start_fresh',
                        help='start fresh (ignore / replace the prefs file)')
    parser.add_option('-v', '--version', action='version')
    # , version=__svnid__
    # also: -h gets a help / usage message
    options = parser.parse_args()[0]  # ignore any args
    fresh_start = options.start_fresh

    app = wx.App()
    win = MainWindow(None, fresh_start)
    win.Show()
    app.MainLoop()


if __name__ == '__main__':
    main()
