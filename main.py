import moderngl as gl
import numpy as np
import pyrr
import glfw
import time
import cython
import objprint
import trimesh


class EventHandler:
    def __init__(self, target_fps):
        self.keys = [False] * 256
        self.mouse_position = np.array([0.0, 0.0])
        self.delta_time = 0

        self.target_fps = target_fps
    
    def key_callback(self, window, key, scancode, action, mods):
        if action == glfw.PRESS:
            self.keys[scancode] = True
        if action == glfw.RELEASE:
            self.keys[scancode] = False
    def update(self):
        glfw.poll_events()
    
    def start_frame(self):
        self.frame_start_time = time.time()

    def end_frame(self):
        self.delta_time = time.time() - self.frame_start_time




class Game:
    def __init__(self, width : int, height : int, title : str, target_fps : float, entry_scene : int):
        glfw.init()
        glfw.window_hint(glfw.DOUBLEBUFFER, glfw.TRUE)
        glfw.window_hint(glfw.CONTEXT_VERSION_MAJOR, 3)
        glfw.window_hint(glfw.CONTEXT_VERSION_MINOR, 3)
        glfw.window_hint(glfw.OPENGL_PROFILE, glfw.OPENGL_CORE_PROFILE)
        self.window = glfw.create_window(width, height, title, None, None)
        glfw.make_context_current(self.window)
        # glfw.swap_interval(1)

        self.context = gl.create_context(require=330)

        self.event_handler = EventHandler(target_fps)
        glfw.set_key_callback(self.window, self.event_handler.key_callback)

        self.current_scene = entry_scene
        self.scenes : list = []
        self.resources : list = []

    def run(self):
        self.scenes[self.current_scene].enter_current(self.window, self.context)
        while self.current_scene != -1:
            self.event_handler.start_frame()
            if glfw.window_should_close(self.window):
                self.current_scene = -1
            self.event_handler.update()
            self.scenes[self.current_scene].update(self.event_handler.delta_time)

            self.scenes[self.current_scene].render(self.window, self.context)

            self.custom_render_pass()

            glfw.swap_buffers(self.window)
            self.event_handler.end_frame()
        
    def custom_render_pass(self):
        pass


class Node:
    def __init__(self, position = np.array([0.0, 0.0, 0.0]), rotation = np.array([0.0, 0.0, 0.0]), scale = np.array([1.0, 1.0, 1.0])):
        self.position = position
        self.rotation = rotation
        self.scale = scale
        self.children : list = []

    def enter_tree(self, window, context):
        for child in self.children:
            child.enter_tree(window, context)

    def leave_tree(self):
        for child in self.children:
            child.leave_tree()

    def update(self, delta_time):
        for child in self.children:
            child.update(delta_time)

    def render(self, window, context):
        for child in self.children:
            child.render(window, context)

class CameraNode(Node):
    def __init__(self, projection, program, position, rotation):
        super().__init__(position, rotation, scale=np.array([1.0, 1.0, 1.0]))
        self.projection = projection
        self.program = program
        self.view = pyrr.matrix44.create_identity()
    def use(self, program):
        self.view = pyrr.matrix44.create_from_translation(self.position) @ pyrr.matrix44.create_from_eulers(self.rotation)
        self.view = pyrr.matrix44.inverse(self.view)

        program.program['view'].write(self.view.astype('f4').tobytes())
        program.program['projection'].write(self.projection.astype('f4').tobytes())

    def enter_tree(self, window, context):
        super().enter_tree(window, context)
        self.use(self.program)    

    def update(self, delta_time):
        super().update(delta_time)

    def render(self, window, context):
        super().render(window, context)



class VisualNode(Node):
    def __init__(self, context : gl.Context, position = np.array([0.0, 0.0, 0.0]), rotation = np.array([0.0, 0.0, 0.0]), scale = np.array([1.0, 1.0, 1.0])):
        super().__init__(position, rotation, scale)
    

    def render(self, window, context):
        super().render(window, context)

class Resource:
    def __init__(self, path):
        self.path = path
        self.loaded = False

    def load(self, window, context):
        self.loaded = True

    def unload(self):
        self.loaded = False

    def load_if_unloaded(self, window, context):
        if not self.loaded:
            self.load(window, context)

class ModelResource(Resource):
    def __init__(self, path):
        super().__init__(path)

    def load(self, window, context : gl.Context):
        self.data = trimesh.load(self.path)
        super().load(window, context)
        self.buffer : gl.Buffer = context.buffer(
            self.data.vertices[self.data.faces].astype(np.float32).tobytes()
        )

    def unload(self):
        del self.data
        super().unload()

class ProgramResource(Resource):
    def __init__(self, path1, path2):
        self.path1 = path1
        self.path2 = path2
        self.loaded = False

    def load(self, window, context : gl.Context):
        self.program : gl.Program = context.program(
            vertex_shader=open(self.path1).read(),
            fragment_shader=open(self.path2).read()
        )

    def unload(self):
        # self.program = None
        pass

class ModelNode(VisualNode):
    def __init__(self, context : gl.Context, model_resource : ModelResource, program_resource : ProgramResource, position = np.array([0.0, 0.0, 0.0]), rotation = np.array([0.0, 0.0, 0.0]), scale = np.array([1.0, 1.0, 1.0])):
        self.model_resource = model_resource
        self.program_resource = program_resource
        super().__init__(context, position, rotation, scale)
        
    def enter_tree(self, window, context):
        self.model_resource.load_if_unloaded(window, context)
        self.program_resource.load_if_unloaded(window, context)
        self.vertex_array_object : gl.VertexArray = context.simple_vertex_array(
            self.program_resource.program,
            self.model_resource.buffer,
            'a_pos'
        )
        super().enter_tree(window, context)
    def leave_tree(self):
        self.model_resource.unload()
        self.program_resource.unload()
        del self.vertex_array_object


    def update(self, delta_time):
        pass

    def render(self, window, context):
        super().render(window, context)
        self.vertex_array_object.render(
            gl.TRIANGLES
        )


class Scene:
    def __init__(self, root_node):
        self.root_node = root_node
    
    def enter_current(self, window, context):
        self.root_node.enter_tree(window, context)

    def leave_current(self):
        self.root_node.leave_tree()

    def update(self, delta_time):
        self.root_node.update(delta_time)

    def render(self, window, context):
        context.clear(0.2, 0.4, 0.6)
        self.root_node.render(window, context)

class TestGame(Game):
    def __init__(self):
        super().__init__(640, 360, "Test Game", 60, entry_scene=0)

        self.resources.append(ModelResource("cube.obj"))
        self.resources.append(ProgramResource("simple.vert", "simple.frag"))
        
        self.resources[-1].load(self.window, self.context)
        print(list(self.resources[-1].program))

        self.scenes.append(Scene(
            ModelNode(
                context=self.context,
                model_resource=self.resources[0],
                program_resource=self.resources[1],
                position=np.array([0.0, 0.0, 0.0]),
                rotation=np.array([0.0, 0.0, 0.0]),
                scale=np.array([1.0, 1.0, 1.0])
            )
        ))

        self.scenes[-1].root_node.children.append(
            CameraNode(
                pyrr.matrix44.create_perspective_projection(
                    60.0, 640.0/360.0, 0.1, 100.0
                ),
                self.resources[1],
                np.array([0.0, 0.0, 5.0]),
                np.array([0.0, 0.0, 0.0])
            )
        )


        self.run()

        # self.resources[-1].unload()

    def custom_render_pass(self):
        return super().custom_render_pass()




game = TestGame()