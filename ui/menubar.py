import ctypes, time
import ctypes.wintypes

from typing import Any

try:
    from ..helper.mutil import Util
    from ..header.h_menubar import h_MenuBar
except ImportError:
    from helper.mutil import Util
    from header.h_menubar import h_MenuBar

# Constants from the Windows API
MF_STRING = 0x00000000
MF_POPUP = 0x00000010
MF_SEPARATOR = 0x00000800
MF_ENABLED = 0x00000000
MF_GRAYED = 0x00000001
MF_DISABLED = 0x00000002
WM_COMMAND = 0x0111
WM_QUIT = 0x0012
WM_DESTROY = 0x0002

# MenuBar class to handle menu creation
class MenuBar(h_MenuBar):
    hwdn: Any
    menu: Any
    menu_items: Any

    def __init__(self, window_handle):
        self.hwnd = window_handle
        self.menu = None
        self.menu_items = {}

    def create_menu(self, menu_definition):
        self.menu = ctypes.windll.user32.CreateMenu()

        for item in menu_definition:
            item_id = item.get('id', 0)
            item_text = item.get('text', '')
            sub_menu = item.get('sub_menu', None)

            if sub_menu:
                submenu = ctypes.windll.user32.CreatePopupMenu()
                self._create_submenu(submenu, sub_menu)
                ctypes.windll.user32.AppendMenuW(self.menu, MF_POPUP, submenu, item_text)
                self.menu_items[item_id] = submenu
            else:
                ctypes.windll.user32.AppendMenuW(self.menu, MF_STRING, item_id, item_text)
                self.menu_items[item_id] = None

        ctypes.windll.user32.SetMenu(self.hwnd, self.menu)


    def _create_submenu(self, submenu, sub_menu_items):
        for sub_item in sub_menu_items:
            sub_item_id = sub_item.get('id', 0)
            sub_item_text = sub_item.get('text', '')

            if sub_item.get('separator', False):
                ctypes.windll.user32.AppendMenuW(submenu, MF_SEPARATOR, sub_item_id, None)
            else:
                ctypes.windll.user32.AppendMenuW(submenu, MF_STRING, sub_item_id, sub_item_text)
                self.menu_items[sub_item_id] = None

    def handle_message(self, msg):
        if msg.message == WM_COMMAND:
            item_id = msg.wParam
            print(f"Menu item clicked: {item_id}")
            # Add functionality here for menu item actions

    def process_windows_messages(self) -> None:
        msg = ctypes.wintypes.MSG()
        ret = ctypes.windll.user32.GetMessageW(ctypes.byref(msg), None, 0, 0)

        ctypes.windll.user32.TranslateMessage(ctypes.byref(msg))
        ctypes.windll.user32.DispatchMessageW(ctypes.byref(msg))


        self.handle_message(msg)

# Usage example:
def main():
    time.sleep(1)
    # Create Pygame window or get its handle
    # For demonstration, assuming a window handle is available
    hwnd = ctypes.windll.user32.GetForegroundWindow()

    # Define menu structure
    menu_definition = [
        {'text': 'File', 'id': 101, 'sub_menu': [
            {'text': 'Open', 'id': 201},
            {'text': 'Save', 'id': 202},
            {'separator': True},
            {'text': 'Exit', 'id': 203}
        ]},
        {'text': 'Edit', 'id': 102, 'sub_menu': [
            {'text': 'Copy', 'id': 301},
            {'text': 'Paste', 'id': 302}
        ]}
        # Add more menu items/submenus as needed
    ]

    # Create MenuBar instance and create the menu
    menu_bar = MenuBar(hwnd)
    menu_bar.create_menu(menu_definition)

    # Main message loop (not included here)
    # Handle messages using menu_bar.handle_message(msg)


if __name__ == "__main__":
    main() # injects menu into whatever the foreground window is