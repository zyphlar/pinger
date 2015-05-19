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
# For IP addresses
import socket, struct

# Vars
startup_active_label = "✓ Start Automatically"
startup_inactive_label = "Start Automatically"
pause_label = "Pause"
play_label = "Resume"
home_path = os.path.expanduser("~")
startup_path = home_path+'/.config/autostart/pinger.desktop'
startup_dir = home_path+'/.config/autostart/'

parser = argparse.ArgumentParser()
parser.add_argument("-t", "--target", help="Target to PING against. (IP / Hostname / Domain name). Defaults to 8.8.8.8")
parser.add_argument("-f", "--freq", help="Timeout between pings, in seconds. Defaults to 5")
parser.add_argument("-m", "--maxlog", help="Maximum amount of pings to log. Defaults to 40")
parser.add_argument("-c", "--color", help="Color scheme ('dark' or 'light'). Defaults to dark.")
args = parser.parse_args()

ubuntu_mono_dark_rgba = [0xdf, 0xd8, 0xc8, 0xff]
ubuntu_mono_light_rgba = [0x3a, 0x39, 0x35, 0xff]
black = [0, 0, 0, 0xff]
red = [0xdf, 0x38, 0x2c, 0xff]
orange = [0xdd, 0x48, 0x14, 0xff]
yellow = [0xef, 0xb7, 0x3e, 0xff]
white = [0xff, 0xff, 0xff, 0xff]
dark_bg = [0, 0, 0, 0x3f]
light_bg = [0xff, 0xff, 0xff, 0x3f]

#accumulate the arguments for use later
arguments = " "
for arg in sys.argv[1:]:
  arguments += arg + " "

# User-editable variables
if args.target:
  default_host = args.target
else:
  print "Using default Internet target of 8.8.8.8"
  default_host = "8.8.8.8" # IP or hostname of WAN

default_router = "192.168.1.1" # IP or hostname of router

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
  danger_color = red
  warning_color = yellow
  graph_highlight = ubuntu_mono_dark_rgba
  graph_background = light_bg
else:
  graph_color = ubuntu_mono_dark_rgba
  danger_color = red
  warning_color = yellow
  graph_highlight = ubuntu_mono_light_rgba
  graph_background = dark_bg

#
# Main Class
#

class Pinger:
  host = None
  router = None
  host_log = []
  router_log = []
  paused = False
  autostart = False
  icon_height = 22

  def ping(self, target, log, widget=None, data=None):
    if not self.paused:
      #print "Pinging "+str(target)
      ping = subprocess.Popen(
          ["ping", "-c", "1", target],
          stdout = subprocess.PIPE,
          stderr = subprocess.PIPE
      )
      out, error = ping.communicate()
      m = re.search('time=(.*) ms', out)
      if error or m == None:
        label = "PING FAIL"
        self.log_ping(log, -1)
      else:
        latency = "%.2f" % float(m.group(1))
        label = latency+" ms"
        self.log_ping(log, latency)

      #self.ind.set_label(label, "100.0 ms")


  def ping_both(self):
    self.ping(self.host, self.host_log)
    self.ping(self.router, self.router_log)
    self.update_log_menu()
    gobject.timeout_add_seconds(self.timeout, self.ping_both)

  def log_ping(self, log, value):
    log.append(float(value))
    # limit the size of the log
    if len(log) >= ping_log_max_size:
      # remove the earliest ping, not the latest
      log.pop(0) 

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

    if len(self.host_log) > 0:
      self.draw_log(ctx, self.host_log, 0)
      host_avg = sum(self.host_log)/len(self.host_log)
      self.ping_menu.set_label("Internet: "+str(int(round(self.host_log[-1])))+" ms "+str(int(round(host_avg)))+" avg")
    if len(self.router_log) > 0:
      self.draw_log(ctx, self.router_log, (self.icon_height/2))
      router_avg = sum(self.router_log)/len(self.router_log)
      self.router_menu.set_label("Router: "+str(int(round(self.router_log[-1])))+" ms "+str(int(round(router_avg)))+" avg")

    try:
      os.remove("/tmp/graph.png")
    except:
      pass
    surface.write_to_png("/tmp/graph.png")
    self.ind.set_icon("") # gotta set it to nothing in order to update
    self.ind.set_icon("graph")
 

  def draw_log(self, ctx, log, yOffset):
    if(max(log) < 100):
      max_ping = 100
    elif(max(log) > 1000):
      max_ping = 1000
    else:
      max_ping = max(log)

    for index, ping in enumerate(log):

      if float(ping) == -1: # Ping error
        # Draw full-height error bar

        self.draw_rect( ctx, [index,(self.icon_height/2)+yOffset], [1,(-self.icon_height/2)-1], danger_color )
      else:
        # draw normal bar
        bar_height = -int(self.scale(ping, (0,max_ping), (0,(self.icon_height/2)-1)))

        if bar_height > -1:
          bar_height = -1

        if ping > 100:
          color = warning_color
        else:
          color = graph_color

        self.draw_rect( ctx, [index,self.icon_height/2+yOffset], [1,bar_height], color )

   
  def draw_rect(self, ctx, point, size, rgba):
    ctx.rectangle( point[0], point[1], size[0], size[1] )
    ctx.set_source_rgba(rgba[0]/float(255), rgba[1]/float(255), rgba[2]/float(255), rgba[3]/float(255))
    ctx.fill()

  def scale(self, val, src, dst):
    """
    Scale the given value from the scale of src to the scale of dst.
    """
    scale = ((val - src[0]) / (src[1]-src[0])) * (dst[1]-dst[0]) + dst[0]
    return scale

  def get_default_gateway_linux(self):
    # Read the default gateway directly from /proc.
    with open("/proc/net/route") as fh:
      for line in fh:
        fields = line.strip().split()
        if fields[1] != '00000000' or not int(fields[3], 16) & 2:
          continue

        return str(socket.inet_ntoa(struct.pack("<L", int(fields[2], 16))))

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
    self.ind.set_icon_theme_path("/tmp")

    # create a menu
    self.menu = Gtk.Menu()
    # with ping numbers
    self.ping_menu = self.create_menu_item("", None)
    self.router_menu = self.create_menu_item("", None)
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

    # load host/router vars
    self.host = default_host

    # set router / gateway dynamically
    self.router = self.get_default_gateway_linux()
    if self.router == None:
      self.router = default_router
    print "Set router target to "+str(self.router)

    # start the ping process
    self.counter = 0
    self.timeout = ping_frequency
    self.ping_both()

    # Print started message
    print "Started."

    # Begin runtime loop
    Gtk.main()

#
# Runtime
#

if __name__ == "__main__":
  pinger = Pinger()
