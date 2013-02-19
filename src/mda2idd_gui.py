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
Choose   File --> Save  (or ^S) 
to write an ASCII text file.

For now, only `*.mda` files may be browsed.
ASCII text files will be written to directory: ../ASCII/
(relative to the MDA file directory)
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
__url__ = "$URL$"
__url__ = "https://subversion.xray.aps.anl.gov/bcdaext/yviewer/"


RC_FILE = ".mda2idd_gui_rc.xml"

class MainWindow(wx.Frame):
    
    def __init__(self, parent=None, start_fresh=False):
        wx.Frame.__init__(self, parent, wx.ID_ANY, u'gui_2idd', wx.DefaultPosition, 
                          wx.Size(200, 100), name=u'root', 
                          style=wx.DEFAULT_FRAME_STYLE)

        self.selectedMdaFile = None
        self.dirty = False
        self.preferences_file = self.GetDefaultPreferencesFileName()
        self.mrud = []      # most-recently-used directories
        
        self.getPreferences(start_fresh)
        
        self._init_menus()
        self._init_contents()
        
        # apply preferences
        self.SetSize(wx.Size(self.prefs['size_h'], self.prefs['size_v']))
        self.SetPosition(wx.Point(self.prefs['pos_h'], self.prefs['pos_v']))
        self.splitter1.SetSashPosition(self.prefs['sash_pos'], True)
        
        self.setStatusText('preferences file: ' + self.preferences_file)
        self.setSummaryText('')
        
    def _init_menus(self):
        id_menu_exit  = 8101 # arbitrary starting number
        id_menu_prefs = 1 + id_menu_exit
        id_menu_about = 1 + id_menu_prefs
        id_menu_save  = 1 + id_menu_about

        self.menu_file = wx.Menu(title='')
        self.menu_file.Append(text=u'&Save\tCtrl+S', id=id_menu_save,
                              help=u'Save MDA data to ASCII text file')
        self.Bind(wx.EVT_MENU, self.OnMenuFileItemSave, id=id_menu_save)
        # TODO: provide a control to let user edit self.preferences_file
        # TODO: provide a control to let user edit self.prefs
#        self.menu_file.AppendSeparator()
#        self.menu_file.Append(text=u'&Preferences ...', id=id_menu_prefs,
#                              help=u'Edit program preferences ...')
#        self.Bind(wx.EVT_MENU, self.OnMenuFileItemPrefs, id=id_menu_prefs)
        self.menu_file.AppendSeparator()
        self.menu_file.Append(text=u'E&xit', id=id_menu_exit,
                              help=u'Quit this application')
        self.Bind(wx.EVT_MENU, self.OnMenuFileItemExit, id=id_menu_exit)

        self.menu_edit = wx.Menu(title='')

        self.menu_help = wx.Menu(title='')
        self.menu_help.Append(text=u'&About ...', id=id_menu_about,
                              help=u'About this application')
        self.Bind(wx.EVT_MENU, self.OnAbout, id=id_menu_about)

        self.menuBar1 = wx.MenuBar()
        self.menuBar1.Append(menu=self.menu_file, title=u'&File')
        self.menuBar1.Append(menu=self.menu_edit, title=u'&Edit')
        self.menuBar1.Append(menu=self.menu_help, title=u'&Help')
        self.SetMenuBar(self.menuBar1)
    
    def _init_contents(self):
        self.statusBar = self.CreateStatusBar()

        self.splitter1 = wx.SplitterWindow(self, id=wx.ID_ANY, style=wx.SP_3D)

        self.textCtrl1 = wx.TextCtrl (self.splitter1, id=wx.ID_ANY, 
                                      style=wx.TE_READONLY|wx.TE_MULTILINE)
        self.setSummaryText('(empty)')

        self.dir = wx.GenericDirCtrl(self.splitter1, wx.ID_ANY, 
                                     dir=self.prefs['start_dir'])
        self.dir.SetFilter(self.prefs['file_filter'])
        # Select the starting folder and expand to it
        self.dir.ExpandPath(self.prefs['start_dir'])
        self.splitter1.SplitVertically(self.dir, self.textCtrl1)
        
        tree = self.dir.GetTreeCtrl()

        wx.EVT_TREE_SEL_CHANGED(self, tree.GetId(), self.OnSelect)
        wx.EVT_SPLITTER_SASH_POS_CHANGED(self, self.splitter1.GetId(), self.OnSashMoved)
        #self.Bind(wx.EVT_SIZE, self.OnWindowGeometryChanged)
        self.Bind(wx.EVT_MOVE, self.OnWindowGeometryChanged)
        
    def GetDefaultPreferencesFileName(self):
        '''return the name of the preferences file for this session'''
        known_os = {
                'Windows': 'USERPROFILE', 
                'Linux': 'HOME',
                'SunOS': 'HOME',
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
        
    def OnSelect(self, event):
        '''user selected something in the directory list'''
        if not isinstance(event, wx.Event):
            self.setStatusText( "Not an event: %s" % str(event) )
            event.Skip()
            return
        selectedItem = self.dir.GetPath()
        self.setStatusText( selectedItem )
        if os.path.exists(selectedItem):
            if os.path.isfile(selectedItem):
                summary = mda2idd_summary.summaryMda(selectedItem)
                self.setSummaryText(summary)
                self.selectedMdaFile = selectedItem
                self.update_mrud(os.path.dirname(selectedItem))
                path = os.path.dirname(selectedItem)
                if path != self.prefs['start_dir']:
                    self.prefs['start_dir'] = path
                    self.update_mrud(path)
            if os.path.isdir(selectedItem):
                self.prefs['start_dir'] = selectedItem
                self.update_mrud(selectedItem)
            self.writePreferences()

    def OnMenuFileItemSave(self, event):
        '''save the selected MDA file as ASCII'''
        if self.selectedMdaFile is not None and os.path.exists(self.selectedMdaFile):
            self.setStatusText("converting MDA file %s to ASCII text" % self.selectedMdaFile)
            mda2idd_report.report(self.selectedMdaFile)
    
    def OnMenuFileItemPrefs(self, event):
        '''save the preferences to a file'''
        pass        # TODO:

    def OnMenuFileItemExit(self, event):
        '''
        User requested to quit the application
        
        :param event: wxPython event object
        '''
        self.Close()
    
    def setSummaryText(self, text):
        '''post new text to the summary TextCtrl, clearing any existing text'''
        #self.textCtrl1.Clear()
        #self.textCtrl1.AppendText(str(text))
        #self.textCtrl1.SetSelection(0,0)	# SetSelection() not working on Linux!
        self.textCtrl1.ChangeValue(str(text))
    
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
        if self.preferences_file is not None:
            if os.path.exists(self.preferences_file):
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
                self.prefs['mrud_max_directories'] = int(node.attrib['max_directories'])
                self.mrud = [subnode.text.strip() for subnode in node.findall('dir')]
                
                self.prefs['file_filter'] = root.find('file_filter').text.strip()
                self.prefs['start_dir'] = root.find('starting_directory').text.strip()
                    

    def writePreferences(self):
        '''save program prefs to a file'''
        if self.preferences_file is not None:
            if os.path.exists(os.path.dirname(self.preferences_file)):

                self.prefs['size_h'], self.prefs['size_v'] = self.GetSize()
                self.prefs['pos_h'],  self.prefs['pos_v']  = self.GetPosition()
            
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
        '''file menu list of most-recently-used directories'''
        if newdir in self.mrud:
            if self.mrud[0] == newdir:
                return
            self.mrud.remove(newdir)
        self.mrud.insert(0, newdir)
        if len(self.mrud) >= self.prefs['mrud_max_directories']:
            self.mrud = self.mrud[:self.prefs['mrud_max_directories']]
        # TODO: manage the MRUD menu items
        
    def OnAbout(self, event):
        '''show the "About" box'''
        # derived from http://wiki.wxpython.org/Using%20wxPython%20Demo%20Code
        # First we create and fill the info object
        info = wx.AboutDialogInfo()
        info.Name = sys.argv[0]
        info.Version = __version__
        #info.Copyright = version.__copyright__
        #info.Copyright = __svnid__
        info.Description = __doc__
        URL = __url__
        info.WebSite = (URL, __svnid__)
        author = __author__ +  " <" + __author_email__ + ">"
        others = [ "author: ", author ]
        # Then we call wx.AboutBox giving it the info object
        wx.AboutBox(info)


def main():
    '''presents the GUI'''
    parser = optparse.OptionParser(description=__description__)
    parser.add_option('-f', '--fresh', action='store_true', default=False,
                        dest='start_fresh',
                        help='start fresh (ignore / replace the prefs file)')
    parser.add_option('-v', '--version', action='version')
    # , version=__svnid__
    # also: -h gets a help / usage message
    options, args = parser.parse_args()
    fresh_start = options.start_fresh

    app = wx.App()
    win = MainWindow(None, fresh_start)
    win.Show()
    app.MainLoop()


if __name__ == '__main__':
    main()
