""" Windows system tray icon.

SysTrayIcon class by Simon Brunning <simon@brunningonline.net>, 2005
"""

from __future__ import print_function

import os
import win32api
import win32con
import win32gui_struct
try:
    import winxpgui as win32gui
except ImportError:
    import win32gui


class SysTrayIcon(object):
    QUIT = 'QUIT'
    SPECIAL_ACTIONS = [QUIT]

    FIRST_ID = 1023

    def __init__(self, icon, hover_text, menu_options, on_quit=None,
                 default_menu_index=None, window_class_name=None,
                 on_click=None):

        self.icon = icon
        self.hover_text = hover_text
        self.on_quit = on_quit
        self.on_click = on_click

        menu_options = menu_options + (('Quit', None, self.QUIT),)
        self._next_action_id = self.FIRST_ID
        self.menu_actions_by_id = set()
        self.menu_options = self._add_ids_to_menu_options(list(menu_options))
        self.menu_actions_by_id = dict(self.menu_actions_by_id)
        del self._next_action_id

        self.default_menu_index = (default_menu_index or 0)
        self.window_class_name = window_class_name or "SysTrayIconPy"

        message_map = {
            win32gui.RegisterWindowMessage("TaskbarCreated"): self.restart,
            win32con.WM_DESTROY: self.destroy,
            win32con.WM_COMMAND: self.command,
            win32con.WM_USER+20: self.notify,
        }
        # Register the Window class.
        window_class = win32gui.WNDCLASS()
        hinst = window_class.hInstance = win32gui.GetModuleHandle(None)
        window_class.lpszClassName = self.window_class_name
        window_class.style = win32con.CS_VREDRAW | win32con.CS_HREDRAW
        window_class.hCursor = win32gui.LoadCursor(0, win32con.IDC_ARROW)
        window_class.hbrBackground = win32con.COLOR_WINDOW
        window_class.lpfnWndProc = message_map  # could also specify a wndproc.
        classAtom = win32gui.RegisterClass(window_class)
        # Create the Window.
        style = win32con.WS_OVERLAPPED | win32con.WS_SYSMENU
        self.hwnd = win32gui.CreateWindow(classAtom, self.window_class_name,
                                          style, 0, 0, win32con.CW_USEDEFAULT,
                                          win32con.CW_USEDEFAULT, 0, 0, hinst,
                                          None)
        win32gui.UpdateWindow(self.hwnd)
        self.notify_id = None
        self.refresh_icon()

        win32gui.PumpMessages()

    def _add_ids_to_menu_options(self, menu_options):
        result = []
        for menu_option in menu_options:
            text, icon, action = menu_option
            if callable(action) or action in self.SPECIAL_ACTIONS:
                self.menu_actions_by_id.add((self._next_action_id, action))
                result.append(menu_option + (self._next_action_id,))
            elif non_string_iterable(action):
                result.append((text, icon,
                               self._add_ids_to_menu_options(action),
                               self._next_action_id))
            else:
                print('Unknown item', text, icon, action)
            self._next_action_id += 1
        return result

    def refresh_icon(self):
        # Try and find a custom icon
        hinst = win32gui.GetModuleHandle(None)
        if os.path.isfile(self.icon):
            icon_flags = win32con.LR_LOADFROMFILE | win32con.LR_DEFAULTSIZE
            hicon = win32gui.LoadImage(hinst, self.icon, win32con.IMAGE_ICON,
                                       0, 0, icon_flags)
        else:
            print("Can't find icon file - using default.")
            hicon = win32gui.LoadIcon(0, win32con.IDI_APPLICATION)

        if self.notify_id:
            message = win32gui.NIM_MODIFY
        else:
            message = win32gui.NIM_ADD
        self.notify_id = (
            self.hwnd, 0,
            win32gui.NIF_ICON | win32gui.NIF_MESSAGE | win32gui.NIF_TIP,
            win32con.WM_USER+20, hicon, self.hover_text)
        win32gui.Shell_NotifyIcon(message, self.notify_id)

    def restart(self, hwnd, msg, wparam, lparam):
        self.refresh_icon()

    def destroy(self, hwnd, msg, wparam, lparam):
        if self.on_quit:
            self.on_quit(self)
        nid = (self.hwnd, 0)
        win32gui.Shell_NotifyIcon(win32gui.NIM_DELETE, nid)
        win32gui.PostQuitMessage(0)  # Terminate the app.

    def notify(self, hwnd, msg, wparam, lparam):
        if lparam == win32con.WM_LBUTTONDBLCLK:
            self.execute_menu_option(self.default_menu_index + self.FIRST_ID)
        elif lparam == win32con.WM_RBUTTONUP:
            self.show_menu()
        elif lparam == win32con.WM_LBUTTONUP:
            if self.on_click:
                self.on_click(self)
        return True

    def show_menu(self):
        menu = win32gui.CreatePopupMenu()
        self.create_menu(menu, self.menu_options)
        #win32gui.SetMenuDefaultItem(menu, 1000, 0)

        pos = win32gui.GetCursorPos()
        # See http://msdn.microsoft.com/library/default.asp?url=/library/en-us/winui/menus_0hdi.asp
        win32gui.SetForegroundWindow(self.hwnd)
        win32gui.TrackPopupMenu(menu, win32con.TPM_LEFTALIGN, pos[0], pos[1],
                                0, self.hwnd, None)
        win32gui.PostMessage(self.hwnd, win32con.WM_NULL, 0, 0)

    def create_menu(self, menu, menu_options):
        for text, icon, action, id in menu_options[::-1]:
            if icon:
                icon = self.prep_menu_icon(icon)

            if id in self.menu_actions_by_id:
                item, extras = win32gui_struct.PackMENUITEMINFO(
                    text=text, hbmpItem=icon, wID=id)
                win32gui.InsertMenuItem(menu, 0, 1, item)
            else:
                submenu = win32gui.CreatePopupMenu()
                self.create_menu(submenu, action)
                item, extras = win32gui_struct.PackMENUITEMINFO(
                    text=text, hbmpItem=icon, hSubMenu=submenu)
                win32gui.InsertMenuItem(menu, 0, 1, item)

    def prep_menu_icon(self, icon):
        # First load the icon.
        ico_x = win32api.GetSystemMetrics(win32con.SM_CXSMICON)
        ico_y = win32api.GetSystemMetrics(win32con.SM_CYSMICON)
        hicon = win32gui.LoadImage(0, icon, win32con.IMAGE_ICON,
                                   ico_x, ico_y, win32con.LR_LOADFROMFILE)

        hdcBitmap = win32gui.CreateCompatibleDC(0)
        hdcScreen = win32gui.GetDC(0)
        hbm = win32gui.CreateCompatibleBitmap(hdcScreen, ico_x, ico_y)
        hbmOld = win32gui.SelectObject(hdcBitmap, hbm)
        # Fill the background.
        brush = win32gui.GetSysColorBrush(win32con.COLOR_MENU)
        win32gui.FillRect(hdcBitmap, (0, 0, 16, 16), brush)
        # unclear if brush needs to be feed.  Best clue I can find is:
        # "GetSysColorBrush returns a cached brush instead of allocating a new
        # one." - implies no DeleteObject
        # draw the icon
        win32gui.DrawIconEx(hdcBitmap, 0, 0, hicon, ico_x, ico_y, 0, 0,
                            win32con.DI_NORMAL)
        win32gui.SelectObject(hdcBitmap, hbmOld)
        win32gui.DeleteDC(hdcBitmap)

        return hbm

    def command(self, hwnd, msg, wparam, lparam):
        id = win32gui.LOWORD(wparam)
        self.execute_menu_option(id)

    def execute_menu_option(self, id):
        menu_action = self.menu_actions_by_id[id]
        if menu_action == self.QUIT:
            win32gui.DestroyWindow(self.hwnd)
        else:
            menu_action(self)


def non_string_iterable(obj):
    try:
        iter(obj)
    except TypeError:
        return False
    else:
        return not isinstance(obj, basestring)
