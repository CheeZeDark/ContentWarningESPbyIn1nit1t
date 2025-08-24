import time
import pygame
import win32api
import win32con
import win32gui
from uniref import WinUniRef


ref = WinUniRef("Content Warning.exe")

def read_list(instance: int) -> list:
    cls_list = ref.find_class_in_image("mscorlib", "System.Collections.Generic.List`1")
    cls_list.set_instance(instance)
    list_items = cls_list.find_field("_items").value
    list_size = cls_list.find_field("_size").value
    return ref.injector.mem_read_pointer_array(list_items + 0x20, list_size)

def get_all_bots() -> list:
    cls_bot_handler = ref.find_class_in_image("Assembly-CSharp", "BotHandler")
    cls_bot_handler.set_instance(cls_bot_handler.find_field("instance").value)

    list_instance = cls_bot_handler.find_field("bots").value
    return read_list(list_instance)

class Vector3:
    x = float(0)
    y = float(0)
    z  = float(0)
    def __init__(self, data: list) -> None:
        self.x = data[0]
        self.y = data[1]
        self.z = data[2]

    def __str__(self) -> str:
        return f"x: {round(self.x, 3)} y: {round(self.y, 3)} z: {round(self.z, 3)}"

def get_transform_instance(obj_instance: int):
    cls_component = ref.find_class_in_image("UnityEngine.CoreModule", "UnityEngine.Component")
    cls_component.set_instance(obj_instance)
    method_get_transform = cls_component.find_method("get_transform")
    return method_get_transform()

def get_object_position(obj_instance: int) -> Vector3:
    cls_transform = ref.find_class_in_image("UnityEngine.CoreModule", "UnityEngine.Transform")
    cls_transform.set_instance(get_transform_instance(obj_instance))
    method_get_position = cls_transform.find_method("get_position_Injected")

    out = ref.injector.mem_alloc()
    method_get_position(args=(out,))
    position = Vector3(ref.injector.mem_read_float_array(out, 3))

    ref.injector.mem_free(out)
    return position

def world_to_screen(pos: Vector3):
    cls_camera = ref.find_class_in_image("UnityEngine.CoreModule", "UnityEngine.Camera")
    cls_camera.set_instance(cls_camera.find_method("get_main")())
    method_world_to_screen = cls_camera.find_method("WorldToScreenPoint_Injected")

    params = ref.injector.mem_alloc()
    ref.injector.mem_write_float_array(params, [pos.x, pos.y, pos.z])

    method_world_to_screen(args=(params, 2, params + 0x100))
    screen = Vector3(ref.injector.mem_read_float_array(params + 0x100, 3))

    ref.injector.mem_free(params)
    return screen

def draw_text(screen, text, size, x, y):
    color = (255, 254, 0)
    font = pygame.font.SysFont("simhei", size)
    text_fmt = font.render(text, 1, color)
    screen.blit(text_fmt, (x, y))


FPS = 60
screen_width = win32api.GetSystemMetrics(0)
screen_height = win32api.GetSystemMetrics(1)

pygame.init()
pygame.mixer.init()
pygame.display.set_caption("Overlay")
screen = pygame.display.set_mode((screen_width, screen_height))
clock = pygame.time.Clock()

bg_color = (0, 0, 0)
hwnd = pygame.display.get_wm_info()["window"]
win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE,
    win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE) | win32con.WS_EX_LAYERED)
win32gui.SetLayeredWindowAttributes(hwnd, win32api.RGB(*bg_color), 0, win32con.LWA_COLORKEY)
win32gui.SetWindowPos(hwnd, win32con.HWND_TOPMOST, 0, 0, 0, 0,
    win32con.SWP_NOMOVE | win32con.SWP_NOSIZE)

while True:
    clock.tick(FPS)
    screen.fill(bg_color)
    screen.set_alpha(128)

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            exit()

    bots = get_all_bots()
    for idx, bot in enumerate(bots):
        world_pos = get_object_position(bot)
        screen_pos = world_to_screen(world_pos)
        screen_x, screen_y = screen_pos.x - 20, screen_height - screen_pos.y - 20

        # check if the target is within the screen
        if screen_x < screen_width and screen_y < screen_height and screen_pos.z >= 0:
            draw_text(screen, f"bot_{idx+1}", 25, screen_x, screen_y)

    pygame.display.flip()
    time.sleep(0.01)
