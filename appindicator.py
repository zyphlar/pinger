#!/usr/bin/env python
#
# Copyright 2009-2012 Canonical Ltd.
#
# Authors: Neil Jagdish Patel <neil.patel@canonical.com>
#          Jono Bacon <jono@ubuntu.com>
#          David Planella <david.planella@ubuntu.com>
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

from gi.repository import Gtk
from gi.repository import AppIndicator3 as appindicator

# Timer
import gobject
# Pinging
import subprocess

# Vars
host = "www.google.com"

class HelloWorld:

  def ping(self, widget=None, data=None):
    ping = subprocess.Popen(
        ["ping", "-c", "1", host],
        stdout = subprocess.PIPE,
        stderr = subprocess.PIPE
    )
    out, error = ping.communicate()
    self.label.set_text(out)
    self.ping_menu_item.set_label(out)
    gobject.timeout_add_seconds(self.timeout, self.ping)

  def delete_event(self, widget, event, data=None):
    # If you return FALSE in the "delete_event" signal handler,
    # GTK will emit the "destroy" signal. Returning TRUE means
    # you don't want the window to be destroyed.
    # This is useful for popping up 'are you sure you want to quit?'
    # type dialogs.
    print "delete event occurred"

    # Change FALSE to TRUE and the main window will not be destroyed
    # with a "delete_event".
    return False

  def destroy(self, widget, data=None):
    print "destroy signal occurred"
    Gtk.main_quit()

  def __init__(self):
    # create a new window
    self.window = Gtk.Window()

    # When the window is given the "delete_event" signal (this is given
    # by the window manager, usually by the "close" option, or on the
    # titlebar), we ask it to call the delete_event () function
    # as defined above. The data passed to the callback
    # function is NULL and is ignored in the callback function.
    self.window.connect("delete_event", self.delete_event)

    # Here we connect the "destroy" event to a signal handler.  
    # This event occurs when we call gtk_widget_destroy() on the window,
    # or if we return FALSE in the "delete_event" callback.
    self.window.connect("destroy", self.destroy)

    # Sets the border width of the window.
    self.window.set_border_width(10)

    # Creates a new button with the label "Hello World".
    self.button = Gtk.Button("Hello World")

    self.label = Gtk.Label(str)

    # When the button receives the "clicked" signal, it will call the
    # function hello() passing it None as its argument.  The hello()
    # function is defined above.
    self.button.connect("clicked", self.ping, None)


    # register a periodic timer
    self.counter = 0
    self.timeout = 1
    gobject.timeout_add_seconds(self.timeout, self.ping)

    # This will cause the window to be destroyed by calling
    # gtk_widget_destroy(window) when "clicked".  Again, the destroy
    # signal could come from here, or the window manager.
    #self.button.connect_object("clicked", Gtk.Widget.destroy, self.window)

    
    self.container = Gtk.Fixed()
    self.container.put(self.button, 0, 0)
    self.button.show()
    self.container.put(self.label, 0, 50)
    self.label.show()
    self.container.show()
    self.window.add(self.container)

    
    # and the window
    self.window.show()

    # and the system tray
    #self.system_tray()

  def main(self):
    # All PyGTK applications must have a Gtk.main(). Control ends here
    # and waits for an event to occur (like a key press or mouse event).
    foo = "bar"

def menuitem_response(w, buf):
  print buf


def create_menu_item(menu, text, callback):

  menu_items = Gtk.MenuItem(text)

  menu.append(menu_items)

  menu_items.connect("activate", callback, text)

  # show the items
  menu_items.show()

  return menu_items

if __name__ == "__main__":
  ind = appindicator.Indicator.new (
                        "example-simple-client",
                        "indicator-messages",
                        appindicator.IndicatorCategory.APPLICATION_STATUS)
  ind.set_status (appindicator.IndicatorStatus.ACTIVE)
  ind.set_attention_icon ("indicator-messages-new")

  # create a menu
  menu = Gtk.Menu()

  # and the app
  hello = HelloWorld()

  # create menu items
  hello.ping_menu_item = create_menu_item(menu, "Ping", hello.ping)
  create_menu_item(menu, "Exit", hello.destroy)

  # Add the menu to our statusbar
  ind.set_menu(menu)

  # Runtime loop
  Gtk.main()
