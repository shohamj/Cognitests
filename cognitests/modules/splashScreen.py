import os
import win32api
import win32gui

import pygame
import win32con


def splash(path):
    os.environ['SDL_VIDEO_CENTERED'] = '1'
    pygame.display.init()
    screen = pygame.display.set_mode((300, 300), pygame.NOFRAME)
    fuchsia = (255, 0, 128)  # Transparency color
    # Set window transparency color
    hwnd = pygame.display.get_wm_info()["window"]
    win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE,
                           win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE) | win32con.WS_EX_LAYERED)
    win32gui.SetLayeredWindowAttributes(hwnd, win32api.RGB(*fuchsia), 0, win32con.LWA_COLORKEY)
    screen.fill(fuchsia)  # Transparent background
    image = pygame.image.load(path)
    image = pygame.transform.scale(image, (300, 300))
    screen.blit(image, (0, 0))
    pygame.display.update()
