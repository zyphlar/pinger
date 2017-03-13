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
      pingResult = Util.doPing(target)
      ssidResult = Util.getSsid()

      print json.dumps({
        'target': target,
        'ssid': ssidResult,
        'loss': float(pingResult['loss']),
        'rtt_avg': float(pingResult['rtt_avg']),
      })

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
    elif platform.system() == "Darwin":
      ssid = subprocess.Popen(["/System/Library/PrivateFrameworks/Apple80211.framework/Versions/Current/Resources/airport","-I"],
          stdout = subprocess.PIPE,
          stderr = subprocess.PIPE
      )
      out, error = ssid.communicate()
      result = out
    return result

  @staticmethod
  def doPing(target):
    if platform.system() == "Linux":
      ping = subprocess.Popen(
          ["ping", "-c", "5", target],
          stdout = subprocess.PIPE,
          stderr = subprocess.PIPE
      )
      pingOut, pingError = ping.communicate()
      # Doing two regexes because Python doesn't like doing both in one
      lossResult = re.search(r' ([0-9]+)% packet loss', pingOut, re.MULTILINE)
      rttAvgResult = re.search(r' = [\d\.]+/([\d\.]+)/[\d\.]+/[\d\.]+', pingOut, re.MULTILINE)
      if pingError:
        output = {'loss':-1, 'rtt_avg':-1};
      else:
        output = {'loss':lossResult.group(1), 'rtt_avg':rttAvgResult.group(1)};
    elif platform.system() == "Darwin": # Macintosh
      ping = subprocess.Popen(
          ["ping", "-c", "5", target],
          stdout = subprocess.PIPE,
          stderr = subprocess.PIPE
      )
      pingOut, error = ping.communicate()
      # print out
      lossResult = re.search(r' ([0-9]+)% packet loss', pingOut, re.MULTILINE)
      rttAvgResult = re.search(r' = [\d\.]+/([\d\.]+)/[\d\.]+/[\d\.]+', pingOut, re.MULTILINE)
      if pingError:
        output = {'loss':-1, 'rtt_avg':-1};
      else:
        output = {'loss':lossResult.group(1), 'rtt_avg':rttAvgResult.group(1)};
    return output

#
# Runtime
#

if __name__ == "__main__":
  pinger = Pinger()
