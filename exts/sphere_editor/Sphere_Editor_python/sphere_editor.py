

import carb
import lula
import numpy as np
import yaml
from isaacsim.core.api.materials import PreviewSurface
from isaacsim.core.api.objects.sphere import VisualSphere
from isaacsim.core.utils.prims import delete_prim, is_prim_path_valid
from isaacsim.core.utils.string import find_unique_string_name
from pxr import Sdf


class SphereEditor:
    def __init__(self):
        self._sphere_path_generators = {}
        self.path_2_spheres = {}

    def _get_collision_sphere_base_path(self, link_path):
        return link_path + "/collision_sphere"

    @staticmethod
    def _path_generator(path: str):
        """Get a generator that incrementally adds integers to `path` forever"""
        count = 1
        while True:
            yield f"{path}_{count}"
            count += 1

    def _get_unused_collision_sphere_path(self, link_path: str):
        sphere_base_path = self._get_collision_sphere_base_path(link_path)

        if sphere_base_path not in self._sphere_path_generators:
            self._sphere_path_generators[sphere_base_path] = self._path_generator(sphere_base_path)

        sphere_path_generator = self._sphere_path_generators[sphere_base_path]
        sphere_path = next(sphere_path_generator)
        while is_prim_path_valid(sphere_path):
            sphere_path = next(sphere_path_generator)
        return sphere_path
    
    def add_sphere(self, link_path, center, radius, store_op=True):
        if not is_prim_path_valid(link_path):
            carb.log_warn("Attempted to add sphere nested under non-existent path")

        if link_path[-1] == "/":
            link_path = link_path[:-1]

        sphere_path = self._get_unused_collision_sphere_path(link_path)


        sphere = VisualSphere(sphere_path, translation=center, radius=radius, color=np.array([1.0, 1.0, 0.0]))

        self.path_2_spheres[sphere.prim_path] = sphere

        # if store_op:
        #     self._operations.append(["ADD", sphere.prim_path])

        return sphere_path