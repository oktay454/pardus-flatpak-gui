#!/usr/bin/env python3
#
# Pardus Flatpak GUI info window module
# Copyright (C) 2020 Erdem Ersoy
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import gettext
import locale
import gi
gi.require_version('Gtk', '3.0')
gi.require_version('Gdk', '3.0')
gi.require_version('GLib', '2.0')
from gi.repository import Gtk, Gdk, GLib

locale.setlocale(locale.LC_ALL, "")
gettext.bindtextdomain("pardus-flatpak-gui", "po/")
gettext.textdomain("pardus-flatpak-gui")
_ = gettext.gettext
gettext.install("pardus-flatpak-gui", "po/")


class InfoWindow(object):
    def __init__(self, application, info_string, app):
        self.Application = application
        self.InfoString = info_string
        self.App = app

        try:
            info_gui_file = "ui/infowindow.glade"
            info_builder = Gtk.Builder.new_from_file(info_gui_file)
            info_builder.connect_signals(self)
        except GLib.GError:
            print(_("Error reading GUI file: ") + info_gui_file)
            raise

        info_text_buffer = info_builder.get_object(
                                    "InfoTextBuffer")
        info_text_buffer.set_text(info_string)

        info_button = info_builder.get_object("InfoButton")
        info_button.set_label(_("_Copy to Clipboard"))

        self.InfoWindow = info_builder.get_object("InfoWindow")
        self.InfoWindow.set_application(application)
        self.InfoWindow.set_title(_("Info About ") + app.get_name())
        self.InfoWindow.show()

    def on_delete_info_window(self, widget, event):
        widget.destroy()

    def on_copy_to_clipboard(self, button):
        clipboard_current = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
        clipboard_current.set_text(self.InfoString, -1)
