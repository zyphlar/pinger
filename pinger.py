#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Pinger.py -- A ping tool that sits in your system tray
# Copyright 2013 Will Bradley
#
# Contributors: Will Bradley <bradley.will@gmail.com>
#               AltF4 <altf4@phx2600.org>
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
# File paths
import os
#Argument parsing
import argparse
#for exit
import sys

# Vars
startup_active_label = "✓ Start Automatically"
startup_inactive_label = "Start Automatically"
pause_label = "Pause"
play_label = "Resume"
home_path = os.path.expanduser("~")
startup_path = home_path+'/.config/autostart/pinger.desktop'
startup_dir = home_path+'/.config/autostart/'

parser = argparse.ArgumentParser()
parser.add_argument("-t", "--target", help="Target to PING against. (IP / Hostname / Domain name). Defaults to 4.2.2.2")
parser.add_argument("-f", "--freq", help="Timeout between pings, in seconds. Defaults to 5")
parser.add_argument("-m", "--maxlog", help="Maximum amount of pings to log. Defaults to 15")
args = parser.parse_args()

#accumulate the arguments for use later
arguments = " "
for arg in sys.argv[1:]:
  arguments += arg + " "

# User-editable variables
if args.target:
  host = args.target
else:
  host = "4.2.2.2" # IP or hostname
  print "Using default target IP of 4.2.2.2"

if args.freq:
  try:
    ping_frequency = int(args.freq)
  except ValueError:
    sys.stderr.write("Error parsing argument '--freq'\n")
    sys.exit(1)
else:
  ping_frequency = 5 # in seconds

if args.maxlog:
  try:
    ping_log_max_size = int(args.maxlog)
  except ValueError:
    sys.stderr.write("Error parsing argument '--maxlog'\n")
    sys.exit(1)
else:
  ping_log_max_size = 15

#
# Main Class
#

class Pinger:
  ping_log = []
  paused = False
  autostart = False

  def ping(self, widget=None, data=None):
    if not self.paused:
      ping = subprocess.Popen(
          ["ping", "-c", "1", host],
          stdout = subprocess.PIPE,
          stderr = subprocess.PIPE
      )
      out, error = ping.communicate()
      m = re.search('time=(.*) ms', out)
      if error or m == None:
        label = "PING FAIL"
        self.log_ping(-1)
      else:
        latency = "%.2f" % float(m.group(1))
        label = latency+" ms"
        self.log_ping(latency)
      self.ind.set_label(label, "100.0 ms")
    gobject.timeout_add_seconds(self.timeout, self.ping)

  def log_ping(self, value):
    self.ping_log.append(value)
    self.update_log_menu()
    # limit the size of the log
    if len(self.ping_log) >= ping_log_max_size:
      # remove the earliest ping, not the latest
      self.ping_log.pop(0) 

  def create_menu_item(self, text, callback):
    menu_item = Gtk.MenuItem(text)
    self.menu.append(menu_item)
    if callback:
      menu_item.connect("activate", callback, text)
    menu_item.show()
    return menu_item

  def destroy(self, widget, data=None):
    print "Quitting..."
    Gtk.main_quit()

  def toggle_autostart(self, widget, data=None):
    if not self.autostart:
      if not os.path.exists(startup_dir):
        os.makedirs(startup_dir)
      with open(startup_path,'w') as f:
        f.write("[Desktop Entry]\r\n"
                "Type=Application\r\n"
                "Exec=python "+os.path.abspath( __file__ )+arguments+"\r\n"
                "X-GNOME-Autostart-enabled=true\r\n"
                "Name=Pinger\r\n"
                "Comment=Pings the internet every few seconds")
      self.autostart = True
      self.startup_menu.set_label(startup_active_label)
    else:
      os.remove(startup_path)
      self.autostart = False
      self.startup_menu.set_label(startup_inactive_label)

  def toggle_pause(self, widget, data=None):
    if self.paused:
      self.paused = False
      self.pause_menu.set_label(pause_label)
    else:
      self.paused = True
      self.pause_menu.set_label(play_label)

  def update_log_menu(self):
    graph = ""
    print self.ping_log
    for p in self.ping_log:
      if float(p) == -1:
        graph += "E "#u'\u2847' # Error
      elif float(p) < 30:
        graph += u'\u2840'
      elif float(p) < 100:
        graph += u'\u2844'
      elif float(p) < 100:
        graph += u'\u2846'
      else:
        graph += u'\u2847'
    self.log_menu.set_label(graph)
    
  def __init__(self):
    # Handle ctrl-c
    signal.signal(signal.SIGINT, self.destroy)

    # Print welcome message
    print "Starting Pinger..."

    # Create systray icon
    self.ind = appindicator.Indicator.new (
               "pinger",
               "", # no icon
               appindicator.IndicatorCategory.COMMUNICATIONS)
    self.ind.set_status (appindicator.IndicatorStatus.ACTIVE)
    self.ind.set_label ("Pinger Loading...", "Pinger Loading...")

    # create a menu
    self.menu = Gtk.Menu()
    # with pause option
    self.pause_menu = self.create_menu_item(pause_label, self.toggle_pause)
    # with autostart option
    # first, check current autostart state by checking existance of .desktop file
    if os.path.exists(startup_path):
      self.autostart = True
      self.startup_menu = self.create_menu_item(startup_active_label, self.toggle_autostart)
    else:
      self.autostart = False
      self.startup_menu = self.create_menu_item(startup_inactive_label, self.toggle_autostart)
    # and log display
    self.log_menu = self.create_menu_item("Ping Log", None)
    # and exit option
    self.create_menu_item("Exit", self.destroy)
    self.ind.set_menu(self.menu)

    # start the ping process
    self.counter = 0
    self.timeout = ping_frequency
    self.ping()

    # Print started message
    print "Started."

    # Begin runtime loop
    Gtk.main()

#
# Runtime
#

if __name__ == "__main__":
  pinger = Pinger()
