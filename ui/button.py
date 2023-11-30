import pygame
from typing import Callable

try:
    from component import Component
    from ..mutil import Util
except ImportError:
    from ui.component import Component
    from mutil import Util

class Button(Component):
    def __init__(self, location: tuple[float, float], size: [float, float] = (100, 40),
                 text: str = "", color: tuple[int, int, int] = (70, 130, 180), 
                 hover_color: tuple[int, int, int] | None = (100, 160, 210), 
                 press_color: tuple[int, int, int] | None = (50, 100, 150),
                 disabled_color: tuple[int, int, int] | None = (150, 150, 150),
                 border_color: tuple[int, int, int] = (0, 0, 0), border_width: int = 1, 
                 border_radius: int = 5, font: pygame.font.Font | None = None,
                 callback: Callable | None = lambda: None, true_conversion: Callable = lambda x, y: (x, y)) -> None:
        
        super().__init__(location, size)
        self._text = text
        self._color = color
        self._hover_color = hover_color if hover_color else color
        self._press_color = press_color if press_color else color
        self._disabled_color = disabled_color if disabled_color else color
        self._border_color = border_color
        self._border_width = border_width
        self._border_radius = border_radius
        self._font = font if font else pygame.font.SysFont("Arial", 20)
        self._callback = callback
        self._true_conversion = true_conversion

        # state
        self._pressed = False
        self._hover = False
        self._disabled = False

    def set_disabled(self, disabled: bool) -> None:
        self._disabled = disabled
    
    def draw(self, surface: pygame.Surface) -> None:
        color = self._color
        if self._disabled:
            color = self._disabled_color
        elif self._pressed:
            color = self._press_color
        elif self._hover:
            color = self._hover_color
        
        pygame.draw.rect(surface, color, (self.location[0], self.location[1], self.size[0], self.size[1]), border_radius=self._border_radius)
        if self._border_width > 0:
            pygame.draw.rect(surface, self._border_color, (self.location[0], self.location[1], self.size[0], self.size[1]), self._border_width, border_radius=self._border_radius)
        
        text = self._font.render(self._text, True, (0, 0, 0))
        surface.blit(text, (self.location[0] + self.size[0] / 2 - text.get_width() / 2, self.location[1] + self.size[1] / 2 - text.get_height() / 2))

    def event(self, event: pygame.event.Event) -> None:
        if self._disabled: return
        pos = self._true_conversion(*pygame.mouse.get_pos())
        if pos[0] < 0 or pos[1] < 0:
            return
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.location[0] <= pos[0] <= self.location[0] + self.size[0] and self.location[1] <= pos[1] <= self.location[1] + self.size[1]:
                self._pressed = True
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            if self._pressed:
                self._callback()
            self._pressed = False
        elif event.type == pygame.MOUSEMOTION:
            if self.location[0] <= pos[0] <= self.location[0] + self.size[0] and self.location[1] <= pos[1] <= self.location[1] + self.size[1]:
                self._hover = True
            else:
                self._hover = False
        else:
            pass