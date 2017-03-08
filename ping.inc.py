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

# Timer

# Date
import datetime
# Pinging
import subprocess
# Regex
import re
# Ctrl-c
import signal
# File paths
import os
# OS naming
import platform
# Argument parsing
import argparse
# For exit
import sys
# For graphing

# For IP addresses
import socket, struct
# For API
import json

#
# Main Class
#

class Pinger:

  def ping(self, target, log=None, widget=None, data=None):
      pingout = Util.doPing(target)
      ssidout = Util.getSsid()

      print json.dumps({'ssid': ssidout, 'loss': int(pingout)})

  def __init__(self):
    # Print welcome message
    print "Starting Pinger..."

    self.ping("4.2.2.2")

    # Print started message
    print "Finished."

#
# Utility class for platform-agnosticism and reusability
#
class Util:
  @staticmethod
  def getSsid():
    if platform.system() == "Linux":
      ssid = subprocess.Popen(["nmcli","-t","-f","active,ssid","dev","wifi"],
          stdout = subprocess.PIPE,
          stderr = subprocess.PIPE
      ) #  | egrep '^yes(.*)' | cut -d\' -f2
      out, error = ssid.communicate()
      m = re.search(r'yes:(.*)', out)
      result = m.group(1)
    elif platform.system() == "Macintosh":
      foo
    return result

  @staticmethod
  def doPing(target):
    if platform.system() == "Linux":
      ping = subprocess.Popen(
          ["ping", "-c", "5", target],
          stdout = subprocess.PIPE,
          stderr = subprocess.PIPE
      )
      out, error = ping.communicate()
      #print out
      m = re.search(r' ([0-9]+)% packet loss', out, re.MULTILINE) # (^rtt .*$)|
      # print m.groups()
      if error or m.group(1) == 100:
        pingout = -1
      else:
        pingout = m.group(1)
    elif platform.system() == "Macintosh":
      foo
    return pingout

#
# Runtime
#

if __name__ == "__main__":
  pinger = Pinger()
