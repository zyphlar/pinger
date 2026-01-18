#!/usr/bin/env python3
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

import datetime
import subprocess
import re
import signal
import os
import argparse
import sys
import time
import cairo
import socket
import struct
import gi

gi.require_version('Gtk', '3.0')
gi.require_version('AppIndicator3', '0.1')
gi.require_version('PangoCairo', '1.0')

from gi.repository import Gtk, GLib, Gio, PangoCairo, Pango
from gi.repository import AppIndicator3 as appindicator

def get_monospace_font():
    """Get available monospace font, preferring Ubuntu Mono."""
    font_map = PangoCairo.FontMap.get_default()
    families = [f.get_name() for f in font_map.list_families()]

    for font in ["Ubuntu Mono", "DejaVu Sans Mono", "Liberation Mono", "Noto Sans Mono", "Consolas", "Courier New"]:
        if font in families:
            return font
    return "monospace"

MONO_FONT = get_monospace_font()

startup_active_label = "✓ Start Automatically"
startup_inactive_label = "Start Automatically"
pause_label = "Pause"
play_label = "Resume"
text_active_label = "✓ Show Text"
text_inactive_label = "Show Text"
home_path = os.path.expanduser("~")
startup_path = home_path+'/.config/autostart/pinger.desktop'
startup_dir = home_path+'/.config/autostart/'

parser = argparse.ArgumentParser()
parser.add_argument("-t", "--target", help="Target to PING against. (IP / Hostname / Domain name). Defaults to 8.8.8.8")
parser.add_argument("-f", "--freq", help="Timeout between pings, in seconds. Defaults to 5")
parser.add_argument("-m", "--maxlog", help="Maximum amount of pings to log. Defaults to 40")
parser.add_argument("-c", "--color", help="Color scheme ('dark' or 'light'). Defaults to dark.")
parser.add_argument("-s", "--size", help="Icon height in pixels. Auto-detected if not specified.")
parser.add_argument("-p", "--padding", help="Panel padding in pixels (default: 8). Used for auto-detection.")
parser.add_argument("--no-text", action="store_true", help="Hide latency text next to chart.")
parser.add_argument("--antialias", choices=["default", "none", "gray", "subpixel"], default="default", help="Font antialias mode.")
parser.add_argument("--hint", choices=["default", "none", "slight", "medium", "full"], default="default", help="Font hint style.")
args = parser.parse_args()

panel_padding = 8
if args.padding:
    try:
        panel_padding = int(args.padding)
    except ValueError:
        pass

def get_panel_settings():
    """Get gnome-panel settings object if available."""
    try:
        source = Gio.SettingsSchemaSource.get_default()
        if source.lookup('org.gnome.gnome-panel.toplevel', True):
            for panel in ['top-panel', 'bottom-panel']:
                try:
                    settings = Gio.Settings.new_with_path(
                        'org.gnome.gnome-panel.toplevel',
                        f'/org/gnome/gnome-panel/layout/toplevels/{panel}/'
                    )
                    if settings.get_int('size') > 0:
                        return settings
                except:
                    continue
    except:
        pass
    return None

def get_panel_height(settings=None):
    """Get panel height from CLI, settings, or default."""
    # 1. CLI argument takes priority
    if args.size:
        try:
            return int(args.size)
        except ValueError:
            pass

    # 2. Try gsettings
    if settings:
        size = settings.get_int('size')
        if size > 0:
            return size - panel_padding

    # 3. Default fallback
    return 22

ubuntu_mono_dark_rgba = [0xdf, 0xd8, 0xc8, 0xff]
ubuntu_mono_light_rgba = [0x3a, 0x39, 0x35, 0xff]
black = [0, 0, 0, 0xff]
red = [0xdf, 0x38, 0x2c, 0xff]
orange = [0xdd, 0x48, 0x14, 0xff]
yellow = [0xef, 0xb7, 0x3e, 0xff]
white = [0xff, 0xff, 0xff, 0xff]
dark_bg = [0, 0, 0, 0x3f]
light_bg = [0xff, 0xff, 0xff, 0x3f]

arguments = " "
for arg in sys.argv[1:]:
  arguments += arg + " "

if args.target:
  default_host = args.target
else:
  print("Using default Internet target of 8.8.8.8")
  default_host = "8.8.8.8"

default_router = "192.168.1.1"

if args.freq:
  try:
    ping_frequency = int(args.freq)
  except ValueError:
    sys.stderr.write("Error parsing argument '--freq'\n")
    sys.exit(1)
else:
  ping_frequency = 5

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

class Pinger:
  host = None
  router = None
  host_log = []
  router_log = []
  paused = False
  autostart = False
  show_text = True
  icon_height = 22
  panel_settings = None


  def start_ping(self, target):
    """Start a ping process without waiting for it."""
    return subprocess.Popen(
        ["ping", "-c", "1", "-W", "1", target],
        stdout = subprocess.PIPE,
        stderr = subprocess.PIPE
    )

  def finish_ping(self, proc, log):
    """Wait for ping process and log the result."""
    out, error = proc.communicate()
    out = out.decode('utf-8')
    error = error.decode('utf-8') if error else ''
    m = re.search(r'time=(.*) ms', out)
    if error or m == None:
      self.log_ping(log, -1)
    else:
      latency = "%.2f" % float(m.group(1))
      self.log_ping(log, latency)

  def ping_both(self):
    start_time = time.monotonic()

    if not self.paused:
      host_proc = self.start_ping(self.host)
      router_proc = self.start_ping(self.router)
      self.finish_ping(host_proc, self.host_log)
      self.finish_ping(router_proc, self.router_log)
    self.update_log_menu()

    # Re-detect gateway after consecutive failures
    if (self.routerLastUpdated != None
      and (datetime.datetime.now()-self.routerLastUpdated).seconds > 60):

      if (len(self.router_log) > 5
        and self.router_log[-1] == -1
        and self.router_log[-2] == -1
        and self.router_log[-3] == -1):

        new_router = self.get_default_gateway_linux()
        if new_router != None:
          self.router = new_router
          print("Updated router target to " + str(self.router))
          self.routerLastUpdated = datetime.datetime.now()

    elapsed = time.monotonic() - start_time
    remaining = max(0, self.timeout - elapsed)
    if remaining > 0:
      GLib.timeout_add(int(remaining * 1000), self.ping_both)
    else:
      GLib.idle_add(self.ping_both)

  def log_ping(self, log, value):
    log.append(float(value))
    if len(log) >= ping_log_max_size:
      log.pop(0)

  def create_menu_item(self, text, callback):
    menu_item = Gtk.MenuItem(label=text)
    self.menu.append(menu_item)
    if callback:
      menu_item.connect("activate", callback, text)
    menu_item.show()
    return menu_item

  def destroy(self, widget, data=None):
    print("Quitting...")
    Gtk.main_quit()

  def on_panel_resize(self, settings, key):
    new_height = get_panel_height(settings)
    if new_height != self.icon_height:
        self.icon_height = new_height
        print("Panel resized, new icon height: " + str(self.icon_height) + "px")
        self.update_log_menu()

  def toggle_autostart(self, widget, data=None):
    if not self.autostart:
      if not os.path.exists(startup_dir):
        os.makedirs(startup_dir)
      with open(startup_path,'w') as f:
        f.write("[Desktop Entry]\r\n"
                "Type=Application\r\n"
                "Exec=python3 "+os.path.abspath( __file__ )+arguments+"\r\n"
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

  def toggle_text(self, widget, data=None):
    self.show_text = not self.show_text
    self.text_menu.set_label(text_active_label if self.show_text else text_inactive_label)
    self.update_log_menu()


  def update_log_menu(self):
    host_text = ""
    router_text = ""
    if len(self.host_log) > 0:
      host_text = " – " if self.host_log[-1] == -1 else str(int(round(self.host_log[-1])))
    if len(self.router_log) > 0:
      router_text = " – " if self.router_log[-1] == -1 else str(int(round(self.router_log[-1])))

    text_margin = 1
    chart_padding = 4
    font_size = self.icon_height * 0.5
    text_width = 0

    if self.show_text:
      temp_surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, 1, 1)
      temp_ctx = cairo.Context(temp_surface)
      temp_ctx.select_font_face(MONO_FONT, cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
      temp_ctx.set_font_size(font_size)
      text_extents = temp_ctx.text_extents("999")
      text_width = int(text_extents.width) + text_margin * 2

    total_width = ping_log_max_size + (chart_padding + text_width if self.show_text else 0)
    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, total_width, self.icon_height)
    ctx = cairo.Context(surface)

    self.draw_rect( ctx, [0,0], [ping_log_max_size,self.icon_height], graph_background )

    section_height = (self.icon_height - 1) // 2
    if len(self.host_log) > 0:
      self.draw_log(ctx, self.host_log, 0, section_height)
      host_avg = sum(self.host_log)/len(self.host_log)
      self.ping_menu.set_label("Internet: "+str(int(round(self.host_log[-1])))+" ms "+str(int(round(host_avg)))+" avg")
    if len(self.router_log) > 0:
      self.draw_log(ctx, self.router_log, section_height + 1, section_height)
      router_avg = sum(self.router_log)/len(self.router_log)
      self.router_menu.set_label("Router: "+str(int(round(self.router_log[-1])))+" ms "+str(int(round(router_avg)))+" avg")

    if self.show_text:
      font_options = cairo.FontOptions()
      hint_map = {"default": cairo.HINT_STYLE_DEFAULT, "none": cairo.HINT_STYLE_NONE,
                  "slight": cairo.HINT_STYLE_SLIGHT, "medium": cairo.HINT_STYLE_MEDIUM, "full": cairo.HINT_STYLE_FULL}
      antialias_map = {"default": cairo.ANTIALIAS_DEFAULT, "none": cairo.ANTIALIAS_NONE,
                       "gray": cairo.ANTIALIAS_GRAY, "subpixel": cairo.ANTIALIAS_SUBPIXEL}
      font_options.set_hint_style(hint_map[args.hint])
      font_options.set_antialias(antialias_map[args.antialias])
      ctx.set_font_options(font_options)
      ctx.select_font_face(MONO_FONT, cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
      ctx.set_font_size(font_size)
      right_edge = total_width - text_margin
      text_area_center = ping_log_max_size + chart_padding + text_width / 2

      if host_text:
        color = danger_color if self.host_log[-1] == -1 else (warning_color if self.host_log[-1] > 100 else graph_color)
        ctx.set_source_rgba(color[0]/255.0, color[1]/255.0, color[2]/255.0, color[3]/255.0)
        host_extents = ctx.text_extents(host_text)
        if self.host_log[-1] == -1:
          ctx.move_to(text_area_center - host_extents.x_advance / 2, self.icon_height * 0.4)
        else:
          ctx.move_to(right_edge - host_extents.x_advance, self.icon_height * 0.4)
        ctx.show_text(host_text)

      if router_text:
        color = danger_color if self.router_log[-1] == -1 else (warning_color if self.router_log[-1] > 100 else graph_color)
        ctx.set_source_rgba(color[0]/255.0, color[1]/255.0, color[2]/255.0, color[3]/255.0)
        router_extents = ctx.text_extents(router_text)
        if self.router_log[-1] == -1:
          ctx.move_to(text_area_center - router_extents.x_advance / 2, self.icon_height * 0.9)
        else:
          ctx.move_to(right_edge - router_extents.x_advance, self.icon_height * 0.9)
        ctx.show_text(router_text)

    try:
      os.remove("/tmp/graph.png")
    except:
      pass
    surface.write_to_png("/tmp/graph.png")
    self.ind.set_icon_full("", "Pinger")  # clear to force refresh
    self.ind.set_icon_full("graph", "Pinger")


  def draw_log(self, ctx, log, yOffset, section_height):
    if(max(log) < 100):
      max_ping = 100
    elif(max(log) > 1000):
      max_ping = 1000
    else:
      max_ping = max(log)

    for index, ping in enumerate(log):
      x = ping_log_max_size - len(log) + index

      if float(ping) == -1:
        self.draw_rect( ctx, [x, section_height + yOffset], [1, -section_height], danger_color )
      else:
        bar_height = -int(self.scale(ping, (0,max_ping), (0, section_height - 1)))

        if bar_height > -1:
          bar_height = -1

        if ping > 100:
          color = warning_color
        else:
          color = graph_color

        self.draw_rect( ctx, [x, section_height + yOffset], [1, bar_height], color )


  def draw_rect(self, ctx, point, size, rgba):
    ctx.rectangle( point[0], point[1], size[0], size[1] )
    ctx.set_source_rgba(rgba[0]/float(255), rgba[1]/float(255), rgba[2]/float(255), rgba[3]/float(255))
    ctx.fill()

  def scale(self, val, src, dst):
    return ((val - src[0]) / (src[1]-src[0])) * (dst[1]-dst[0]) + dst[0]

  def get_default_gateway_linux(self):
    with open("/proc/net/route") as fh:
      for line in fh:
        fields = line.strip().split()
        if fields[1] != '00000000' or not int(fields[3], 16) & 2:
          continue

        return str(socket.inet_ntoa(struct.pack("<L", int(fields[2], 16))))

  def __init__(self):
    signal.signal(signal.SIGINT, self.destroy)

    self.panel_settings = get_panel_settings()
    self.icon_height = get_panel_height(self.panel_settings)
    if self.panel_settings:
        self.panel_settings.connect('changed::size', self.on_panel_resize)

    print("Starting Pinger...")
    print("Icon height: " + str(self.icon_height) + "px")
    print("Ping frequency: " + str(ping_frequency) + "s")
    print("Using font: " + MONO_FONT)

    self.ind = appindicator.Indicator.new(
               "pinger",
               "",
               appindicator.IndicatorCategory.SYSTEM_SERVICES)
    self.ind.set_status(appindicator.IndicatorStatus.ACTIVE)
    self.ind.set_icon_theme_path("/tmp")

    self.show_text = not args.no_text

    self.menu = Gtk.Menu()
    self.ping_menu = self.create_menu_item("", None)
    self.router_menu = self.create_menu_item("", None)
    self.pause_menu = self.create_menu_item(pause_label, self.toggle_pause)
    self.text_menu = self.create_menu_item(text_active_label if self.show_text else text_inactive_label, self.toggle_text)
    if os.path.exists(startup_path):
      self.autostart = True
      self.startup_menu = self.create_menu_item(startup_active_label, self.toggle_autostart)
    else:
      self.autostart = False
      self.startup_menu = self.create_menu_item(startup_inactive_label, self.toggle_autostart)
    self.create_menu_item("Exit", self.destroy)
    self.ind.set_menu(self.menu)

    self.host = default_host
    self.router = self.get_default_gateway_linux()
    if self.router == None:
      self.router = default_router
    print("Set router target to " + str(self.router))
    self.routerLastUpdated = datetime.datetime.now()

    self.counter = 0
    self.timeout = ping_frequency
    self.ping_both()

    print("Started.")
    Gtk.main()

if __name__ == "__main__":
  pinger = Pinger()
