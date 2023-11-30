import pygame

class Component:
    def __init__(self, location: tuple[float, float], size: [float, float], *args, **kwargs) -> None:
        self.location = location
        self.size = size
    
    def draw(self, surface: pygame.Surface) -> None:
        pass

    def event(self, event: pygame.event.Event) -> None:
        pass