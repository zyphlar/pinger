#!/usr/bin/env python
#
# Pinger.py -- A ping tool that sits in your system tray
# Copyright 2013 Will Bradley
#
# Authors: Will Bradley <bradley.will@gmail.com>
#
# This program is free software: you can redistribute it and/or modify it 
# under the terms of either or both of the following licenses:
#
# 1) the GNU Lesser General Public License version 3, as published by the 
# Free Software Foundation; and/or
# 2) the GNU Lesser General Public License version 2.1, as published by 
# the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful, but 
# WITHOUT ANY WARRANTY; without even the implied warranties of 
# MERCHANTABILITY, SATISFACTORY QUALITY or FITNESS FOR A PARTICULAR 
# PURPOSE.  See the applicable version of the GNU Lesser General Public 
# License for more details.
#
# You should have received a copy of both the GNU Lesser General Public 
# License version 3 and version 2.1 along with this program.  If not, see 
# <http://www.gnu.org/licenses/>
#

# User-editable variables
host = "4.2.2.2" # IP or hostname
ping_frequency = 5 # in seconds

#
# Dependencies
#

# System Tray Icon
from gi.repository import Gtk
from gi.repository import AppIndicator3 as appindicator
# Timer
from gi.repository import GObject as gobject
# Pinging
import subprocess
# Regex
import re
# Ctrl-c
import signal

#
# Main Class
#

class Pinger:

  def ping(self, widget=None, data=None):
    ping = subprocess.Popen(
        ["ping", "-c", "1", host],
        stdout = subprocess.PIPE,
        stderr = subprocess.PIPE
    )
    out, error = ping.communicate()
    if error:
      label = "PING FAIL"
    else:
      m = re.search('time=(.*) ms', out)
      label = m.group(1)+" ms"
    self.ind.set_label (label, "100.0 ms")
    #self.ping_menu_item.set_label(out)
    gobject.timeout_add_seconds(self.timeout, self.ping)

  def create_menu_item(self, text, callback):
    menu_item = Gtk.MenuItem(text)
    self.menu.append(menu_item)
    menu_item.connect("activate", callback, text)
    menu_item.show()

  def destroy(self, widget, data=None):
    print "destroy signal occurred"
    Gtk.main_quit()

  def __init__(self):
    # Handle ctrl-c
    signal.signal(signal.SIGINT, self.destroy)

    # Create systray icon
    self.ind = appindicator.Indicator.new (
               "pinger",
               "", # no icon
               appindicator.IndicatorCategory.COMMUNICATIONS)
    self.ind.set_status (appindicator.IndicatorStatus.ACTIVE)
    self.ind.set_label ("Pinger Loading...", "Pinger Loading...")

    # create a menu
    self.menu = Gtk.Menu()
    self.create_menu_item("Exit", self.destroy)
    self.ind.set_menu(self.menu)

    # start the ping process
    self.counter = 0
    self.timeout = ping_frequency
    self.ping()

    # Begin runtime loop
    Gtk.main()

#
# Runtime
#

if __name__ == "__main__":
  pinger = Pinger()
