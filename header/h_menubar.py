from typing import Any

MF_STRING = 0x00000000
MF_POPUP = 0x00000010
MF_SEPARATOR = 0x00000800
MF_ENABLED = 0x00000000
MF_GRAYED = 0x00000001
MF_DISABLED = 0x00000002
WM_COMMAND = 0x0111
WM_QUIT = 0x0012
WM_DESTROY = 0x0002


class h_MenuBar:
    hwdn: Any
    menu: Any
    menu_items: Any

    def __init__(self, window_handle): ...
    def create_menu(self, menu_definition): ...        
    def _create_submenu(self, submenu, sub_menu_items): ...
    def handle_message(self, msg): ...
    def _message_loop(self) -> None: ...