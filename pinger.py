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
# Argument parsing
import argparse
# For exit
import sys
# For graphing
import cairo

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
parser.add_argument("-m", "--maxlog", help="Maximum amount of pings to log. Defaults to 40")
parser.add_argument("-c", "--color", help="Color scheme ('dark' or 'light'). Defaults to dark.")
args = parser.parse_args()

ubuntu_mono_dark_rgba = [0xdf, 0xd8, 0xc8, 0xff]
ubuntu_mono_light_rgba = [0x3a, 0x39, 0x35, 0xff]
black = [0, 0, 0, 0xff]
red = [0xff, 0, 0, 0xff]
white = [0xff, 0xff, 0xff, 0xff]
dark_bg = [0, 0, 0, 0x3f]
light_bg = [0xff, 0xff, 0xff, 0x3f]

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
  ping_log_max_size = 40

if args.color == "light":
  graph_color = ubuntu_mono_light_rgba
  graph_highlight = ubuntu_mono_dark_rgba
  graph_background = light_bg
else:
  graph_color = ubuntu_mono_dark_rgba
  graph_highlight = ubuntu_mono_light_rgba
  graph_background = dark_bg

#
# Main Class
#

class Pinger:
  ping_log = []
  paused = False
  autostart = False
  icon_height = 22

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
      #self.ind.set_label(label, "100.0 ms")
    gobject.timeout_add_seconds(self.timeout, self.ping)

  def log_ping(self, value):
    self.ping_log.append(float(value))
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
    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, ping_log_max_size, self.icon_height)
    ctx = cairo.Context(surface)

    # draw semitransparent box
    self.draw_rect( ctx, [0,0], [ping_log_max_size,self.icon_height], graph_background )

    if(max(self.ping_log) < 100):
      max_ping = 100
    else:
      max_ping = max(self.ping_log)

    for index, ping in enumerate(self.ping_log):

      if float(ping) == -1: # Ping error
        # Draw full-height error bar
        self.draw_rect( ctx, [index,self.icon_height], [1,-self.icon_height-1], red )
      else:
        # draw normal bar
        self.draw_rect( ctx, [index,self.icon_height], [1,-int(self.scale(ping, (0,max_ping), (0,self.icon_height)))], graph_color )

    os.remove("graph.png")
    surface.write_to_png("graph.png")
    self.ind.set_icon("") # gotta set it to nothing in order to update
    self.ind.set_icon("graph")
    self.ping_menu.set_label("Ping: "+str(self.ping_log[-1])+" ms")
    
  def draw_rect(self, ctx, point, size, rgba):
    ctx.rectangle( point[0], point[1], size[0], size[1] )
    ctx.set_source_rgba(rgba[0]/float(255), rgba[1]/float(255), rgba[2]/float(255), rgba[3]/float(255))
    ctx.fill()

  def scale(self, val, src, dst):
    """
    Scale the given value from the scale of src to the scale of dst.
    """
    return ((val - src[0]) / (src[1]-src[0])) * (dst[1]-dst[0]) + dst[0]

  def __init__(self):
    # Handle ctrl-c
    signal.signal(signal.SIGINT, self.destroy)

    # Print welcome message
    print "Starting Pinger..."

    # Create systray icon
    self.ind = appindicator.Indicator.new (
               "pinger",
               "", # no icon
               appindicator.IndicatorCategory.SYSTEM_SERVICES)
    self.ind.set_status (appindicator.IndicatorStatus.ACTIVE)
    #self.ind.set_label ("Pinger Loading...", "Pinger Loading...")
    self.ind.set_icon_theme_path(os.path.dirname(os.path.realpath(__file__)))

    # create a menu
    self.menu = Gtk.Menu()
    # with ping numbers
    self.ping_menu = self.create_menu_item("", None)
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
