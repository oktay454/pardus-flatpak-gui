#!/usr/bin/env python3
#
# Pardus Flatpak GUI uninstall from file window module
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
import threading
import time
import gi
gi.require_version('Gtk', '3.0')
gi.require_version('GLib', '2.0')
gi.require_version('Flatpak', '1.0')
gi.require_version('Gio', '2.0')
from gi.repository import Gtk, GLib, Flatpak, Gio

locale.setlocale(locale.LC_ALL, "")
gettext.bindtextdomain("pardus-flatpak-gui", "/usr/share/locale/")
gettext.textdomain("pardus-flatpak-gui")
_ = gettext.gettext
gettext.install("pardus-flatpak-gui", "/usr/share/locale/")


class UninstallWindow(object):
    def __init__(self, application, flatpak_installation, real_name, arch, branch,
                 tree_model, tree_iter, selection, search_filter, show_button,
                 button_not_pressed_already):
        self.Application = application

        self.RealName = real_name
        self.Arch = arch
        self.Branch = branch
        self.RefFormat = "app/" + self.RealName + "/" + self.Arch + "/" + self.Branch

        self.FlatpakInstallation = flatpak_installation
        self.FlatpakTransaction = \
            Flatpak.Transaction.new_for_installation(
                self.FlatpakInstallation,
                Gio.Cancellable.new())
        self.FlatpakTransaction.set_default_arch(self.Arch)
        self.FlatpakTransaction.set_disable_dependencies(False)
        self.FlatpakTransaction.set_disable_prune(False)
        self.FlatpakTransaction.set_disable_related(False)
        self.FlatpakTransaction.set_disable_static_deltas(False)
        self.FlatpakTransaction.set_no_deploy(False)
        self.FlatpakTransaction.set_no_pull(False)
        self.FlatpakTransaction.add_uninstall(self.RefFormat)

        self.TreeModel = tree_model
        self.TreeIter = tree_iter
        self.Selection = selection
        self.SearchFilter = search_filter
        self.HeaderBarShowButton = show_button
        self.ButtonNotPressedAlready = button_not_pressed_already

        self.FlatHubRefs = self.FlatpakInstallation.list_remote_refs_sync("flathub", Gio.Cancellable.new())

        self.handler_id = self.FlatpakTransaction.connect(
            "new-operation",
            self.uninstall_progress_callback)
        self.handler_id_2 = self.FlatpakTransaction.connect(
            "operation-done",
            self.uninstall_progress_callback_done)
        self.handler_id_error = self.FlatpakTransaction.connect(
            "operation-error",
            self.uninstall_progress_callback_error)

        try:
            uninstall_gui_file = "/usr/share/pardus/pardus-flatpak-gui/ui/actionwindow.glade"
            uninstall_builder = Gtk.Builder.new_from_file(uninstall_gui_file)
            uninstall_builder.connect_signals(self)
        except GLib.GError:
            print(_("Error reading GUI file: ") + uninstall_gui_file)
            raise

        self.UninstallCancellation = Gio.Cancellable.new()

        self.UninstallWindow = uninstall_builder.get_object("ActionWindow")
        self.UninstallWindow.set_application(self.Application)
        self.UninstallWindow.set_title(_("Uninstalling..."))
        self.UninstallWindow.show()

        self.UninstallButtonCancel = uninstall_builder.get_object("ActionButtonCancel")
        self.UninstallButtonCancel.set_sensitive(True)

        self.UninstallProgressBar = uninstall_builder.get_object(
                                        "ActionProgressBar")
        self.ProgressBarValue = int(
            self.UninstallProgressBar.get_fraction() * 100)

        self.UninstallLabel = uninstall_builder.get_object("ActionLabel")
        self.UninstallTextBuffer = uninstall_builder.get_object(
                                       "ActionTextBuffer")

        self.UninstallTextBuffer.set_text("\0", -1)
        self.StatusText = _("Uninstalling...")
        self.UninstallLabel.set_text(self.StatusText)
        self.UninstallTextBuffer.set_text(self.StatusText)

        self.UninstallThread = threading.Thread(
                           target=self.uninstall,
                           args=())
        self.UninstallThread.start()
        GLib.threads_init()

    def uninstall(self):
        GLib.idle_add(self.Selection.unselect_all,
                      data=None,
                      priority=GLib.PRIORITY_DEFAULT)
        time.sleep(0.2)

        handler_id_cancel = self.UninstallCancellation.connect(self.cancellation_callback, None)
        try:
            self.FlatpakTransaction.run(self.UninstallCancellation)
        except GLib.Error:
            status_text = _("Error at uninstalling!")
            self.StatusText = self.StatusText + "\n" + status_text
            GLib.idle_add(self.UninstallLabel.set_text,
                          status_text,
                          priority=GLib.PRIORITY_DEFAULT)
            GLib.idle_add(self.UninstallTextBuffer.set_text,
                          self.StatusText,
                          priority=GLib.PRIORITY_DEFAULT)
            self.disconnect_handlers(handler_id_cancel)
            UninstallWindow.at_uninstallation = False
            return None
        else:
            status_text = _("Uninstalling completed!")
            self.StatusText = self.StatusText + "\n" + status_text
            GLib.idle_add(self.UninstallLabel.set_text,
                          status_text,
                          priority=GLib.PRIORITY_DEFAULT)
            GLib.idle_add(self.UninstallTextBuffer.set_text,
                          self.StatusText,
                          priority=GLib.PRIORITY_DEFAULT)
        time.sleep(0.2)
        self.disconnect_handlers(handler_id_cancel)
        GLib.idle_add(self.UninstallButtonCancel.set_sensitive,
                      False,
                      priority=GLib.PRIORITY_DEFAULT)
        time.sleep(0.5)

        if self.ButtonNotPressedAlready:
            pass
        elif not self.HeaderBarShowButton.get_active():
            GLib.idle_add(self.HeaderBarShowButton.set_active,
                          True,
                          priority=GLib.PRIORITY_DEFAULT)
            time.sleep(0.2)

            GLib.idle_add(self.Selection.unselect_all,
                      data=None,
                      priority=GLib.PRIORITY_DEFAULT)

    def uninstall_progress_callback(self, transaction, operation, progress):
        ref_to_uninstall = Flatpak.Ref.parse(operation.get_ref())
        ref_to_uninstall_real_name = ref_to_uninstall.get_name()

        status_text = _("Uninstalling: ") + ref_to_uninstall_real_name
        self.StatusText = self.StatusText + "\n" + status_text
        GLib.idle_add(self.UninstallLabel.set_text,
                      status_text,
                      priority=GLib.PRIORITY_DEFAULT)
        GLib.idle_add(self.UninstallTextBuffer.set_text,
                      self.StatusText,
                      priority=GLib.PRIORITY_DEFAULT)

        self.TransactionProgress = progress  # FIXME: Fix PyCharm warning
        self.TransactionProgress.set_update_frequency(200)
        self.handler_id_progress = self.TransactionProgress.connect(
            "changed",
            self.progress_bar_update)  # FIXME: Fix PyCharm warning

    def uninstall_progress_callback_done(self, transaction, operation, commit, result):
        self.TransactionProgress.disconnect(self.handler_id_progress)

        operation_ref = Flatpak.Ref.parse(operation.get_ref())
        operation_ref_real_name = operation_ref.get_name()
        operation_ref_arch = operation_ref.get_arch()
        operation_ref_branch = operation_ref.get_branch()
        for uninstalled_ref in self.FlatHubRefs:
            if uninstalled_ref.get_name() == operation_ref_real_name and \
               uninstalled_ref.get_arch() == operation_ref_arch and \
               uninstalled_ref.get_branch() == operation_ref_branch and \
               uninstalled_ref.get_kind() == Flatpak.RefKind.APP:
                uninstalled_ref_real_name = uninstalled_ref.get_name()
                uninstalled_ref_arch = uninstalled_ref.get_arch()
                uninstalled_ref_branch = uninstalled_ref.get_branch()
                uninstalled_ref_remote = "FlatHub"

                installed_size = uninstalled_ref.get_installed_size()
                installed_size_mib = installed_size / 1048576
                installed_size_mib_str = \
                    f"{installed_size_mib:.2f}" + " MiB"

                download_size = uninstalled_ref.get_download_size()
                download_size_mib = download_size / 1048576
                download_size_mib_str = f"{download_size_mib:.2f}" + " MiB"

                name = ""

                tree_model = self.TreeModel.get_model()
                tree_iter = tree_model.get_iter_first()
                while tree_iter:
                    real_name = tree_model.get_value(tree_iter, 0)
                    arch = tree_model.get_value(tree_iter, 1)
                    branch = tree_model.get_value(tree_iter, 2)
                    if real_name == uninstalled_ref_real_name and \
                       arch == uninstalled_ref_arch and \
                       branch == uninstalled_ref_branch:
                        GLib.idle_add(tree_model.set_row,
                                      tree_iter, [uninstalled_ref_real_name,
                                                  uninstalled_ref_arch,
                                                  uninstalled_ref_branch,
                                                  uninstalled_ref_remote,
                                                  installed_size_mib_str,
                                                  download_size_mib_str,
                                                  name],
                                      priority=GLib.PRIORITY_DEFAULT)
                        time.sleep(0.2)

                        tree_model.refilter()
                        time.sleep(0.3)
                    tree_iter = tree_model.iter_next(tree_iter)

    def uninstall_progress_callback_error(self, transaction, operation, error, details):
        ref_to_uninstall = Flatpak.Ref.parse(operation.get_ref())
        ref_to_uninstall_real_name = ref_to_uninstall.get_name()

        status_text = _("Not uninstalled: ") + ref_to_uninstall_real_name
        self.StatusText = self.StatusText + "\n" + status_text
        GLib.idle_add(self.UninstallLabel.set_text,
                      status_text,
                      priority=GLib.PRIORITY_DEFAULT)
        GLib.idle_add(self.UninstallTextBuffer.set_text,
                      self.StatusText,
                      priority=GLib.PRIORITY_DEFAULT)

        if ref_to_uninstall_real_name != self.RealName:
            return True
        else:
            return False

    def progress_bar_update(self, transaction_progress):
        GLib.idle_add(self.UninstallProgressBar.set_fraction,
                      float(transaction_progress.get_progress()) / 100.0,
                      priority=GLib.PRIORITY_DEFAULT)

    def cancellation_callback(self, *data):
        status_text = _("Uninstalling canceled!")
        self.StatusText = self.StatusText + "\n" + status_text
        GLib.idle_add(self.UninstallLabel.set_text,
                      status_text,
                      priority=GLib.PRIORITY_DEFAULT)
        GLib.idle_add(self.UninstallTextBuffer.set_text,
                      self.StatusText,
                      priority=GLib.PRIORITY_DEFAULT)

    def disconnect_handlers(self, handler_id_cancel):
        self.UninstallCancellation.disconnect(handler_id_cancel)
        self.FlatpakTransaction.disconnect(self.handler_id)
        self.FlatpakTransaction.disconnect(self.handler_id_2)
        self.FlatpakTransaction.disconnect(self.handler_id_error)

    def on_press_cancel(self, button):
        self.UninstallCancellation.cancel()
        self.UninstallWindow.hide_on_delete()

    def on_delete_action_window(self, widget, event):
        self.UninstallCancellation.cancel()
        widget.hide_on_delete()
