import moderngl as gl
import numpy as np
import glfw
import time
import cython
from enum import Enum
import trimesh
import objprint

class EventHandler:
    def __init__(self, target_fps):
        self.keys = [False] * 256
        self.mouse_position = np.array([0.0, 0.0])
        self.delta_time = 0

        self.target_fps = target_fps
    
    def key_callback(self, window, key, scancode, action, mods):
        if action == glfw.PRESS:
            self.keys[key] = True
        if action == glfw.RELEASE:
            self.keys[key] = False
    def update(self):
        glfw.poll_events()
    
    def start_frame(self):
        self.frame_start_time = time.time()

    def end_frame(self):
        self.delta_time = time.time()




class Game:
    def __init__(self, width : int, height : int, title : str, target_fps : float, entry_scene : int):
        glfw.init()
        self.window = glfw.create_window(width, height, title, None, None)
        glfw.make_context_current(self.window)
        glfw.swap_interval(1)

        self.ctx = gl.create_context()

        self.event_handler = EventHandler(target_fps)
        glfw.set_key_callback(self.window, self.event_handler.key_callback)

        self.current_scene = entry_scene
        self.scenes : list = []
        self.resources : list = []

    def run(self):
        while self.current_scene != -1:
            self.event_handler.start_frame()
            if glfw.window_should_close(self.window):
                self.current_scene = -1
            self.event_handler.update()
            self.scenes[self.current_scene].update(self.event_handler.delta_time)

            self.scenes[self.current_scene].render(self.window, self.ctx)

            self.custom_render_pass()

            glfw.swap_buffers(self.window)
            self.event_handler.end_frame()
        
    def custom_render_pass(self):
        pass


class Vec3:
    def __init__(self, x, y, z):
        self.x = x
        self.y = y
        self.z = z

class Node:
    def __init__(self, position : Vec3 = Vec3(1.0, 1.0, 1.0), rotation : Vec3 = Vec3(1.0, 1.0, 1.0), scale = Vec3(1.0, 1.0, 1.0)):
        self.position : Vec3 = position
        self.rotation : Vec3 = rotation
        self.scale : Vec3 = scale

    def update(self, delta_time):
        pass

    def render(self, window, context):
        pass

class VisualNode(Node):
    def __init__(self, context : gl.Context, position : Vec3 = Vec3(1.0, 1.0, 1.0), rotation : Vec3 = Vec3(1.0, 1.0, 1.0), scale = Vec3(1.0, 1.0, 1.0)):
        super().__init__(position, rotation, scale)
    

    def render(self, window, context):
        pass

class Resource:
    def __init__(self, path):
        self.path = path

    def load(self):
        pass

    def unload(self):
        pass

class ModelResource(Resource):
    def __init__(self, path):
        self.path = path

    def load(self):
        self.data = trimesh.load(self.path)
        objprint.op(self.data)

    def unload(self):
        # trimesh.release(self.data)
        pass

class Scene:
    def __init__(self, root_node_type):
        self.root_node = root_node_type()
    
    def update(self, delta_time):
        self.root_node.update(delta_time)

    def render(self, window, context):
        self.root_node.render(window, context)

class TestGame(Game):
    def __init__(self):
        super().__init__(640, 360, "Test Game", 60, 0)

        self.scenes.append(Scene(
            Node
        ))

        self.resources.append(ModelResource("cube.obj"))
        self.resources[-1].load()
        self.resources[-1].unload()
        
        self.run()

    def custom_render_pass(self):
        return super().custom_render_pass()



game = TestGame()