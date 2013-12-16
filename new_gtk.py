import gtk

class Main(gtk.Window):

    def __init__(self):
        super(Main, self).__init__()
        self.connect('delete-event', self.on_delete_event)
        self.set_title("Virtual Machine Monitor")
        self.set_position(gtk.WIN_POS_CENTER)
        self.set_default_size(640,600)
        self.set_geometry_hints(min_width=640, min_height=600)
        self.set_icon_from_file("activity.png")
        #menubar = self.add_menubar()

        pixbuf = gtk.gdk.pixbuf_new_from_file_at_size("activity.png",25,25)
        statusicon = gtk.StatusIcon()
        statusicon.set_title("0.0 ms")
        statusicon = gtk.status_icon_new_from_pixbuf(pixbuf)
        statusicon.connect("activate",self.tray_activate)
        self.show_all()

    def on_delete_event(self, widget, event):
        self.hide()
        return True    

    def tray_activate(self, widget):
        self.present()


if __name__ == "__main__":
    Main()
    gtk.main()