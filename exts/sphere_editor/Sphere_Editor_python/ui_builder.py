# Copyright (c) 2022-2024, NVIDIA CORPORATION. All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto. Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#

import omni.timeline
import omni.ui as ui
from isaacsim.core.api.world import World
from isaacsim.core.prims import SingleXFormPrim
from isaacsim.core.utils.stage import create_new_stage, get_current_stage
from isaacsim.examples.extension.core_connectors import LoadButton, ResetButton
from isaacsim.gui.components.element_wrappers import CollapsableFrame, StateButton
from isaacsim.gui.components.ui_utils import get_style
from omni.usd import StageEventType
from pxr import Sdf, UsdLux

from .scenario import FrankaRmpFlowExampleScript


class UIBuilder:
    def __init__(self):
        # Frames are sub-windows that can contain multiple UI elements
        self.frames = []
        # UI elements created using a UIElementWrapper instance
        self.wrapped_ui_elements = []

        # Get access to the timeline to control stop/pause/play programmatically
        self._timeline = omni.timeline.get_timeline_interface()

        # Run initialization for the provided example
        self._on_init()

    ###################################################################################
    #           The Functions Below Are Called Automatically By extension.py
    ###################################################################################

    def on_menu_callback(self):
        """Callback for when the UI is opened from the toolbar.
        This is called directly after build_ui().
        """
        pass

    def on_timeline_event(self, event):
        """Callback for Timeline events (Play, Pause, Stop)

        Args:
            event (omni.timeline.TimelineEventType): Event Type
        """
        if event.type == int(omni.timeline.TimelineEventType.STOP):
            # When the user hits the stop button through the UI, they will inevitably discover edge cases where things break
            # For complete robustness, the user should resolve those edge cases here
            # In general, for extensions based off this template, there is no value to having the user click the play/stop
            # button instead of using the Load/Reset/Run buttons provided.
            self._scenario_state_btn.reset()
            self._scenario_state_btn.enabled = False

    def on_physics_step(self, step: float):
        """Callback for Physics Step.
        Physics steps only occur when the timeline is playing

        Args:
            step (float): Size of physics step
        """
        pass

    def on_stage_event(self, event):
        """Callback for Stage Events

        Args:
            event (omni.usd.StageEventType): Event Type
        """
        if event.type == int(StageEventType.OPENED):
            # If the user opens a new stage, the extension should completely reset
            self._reset_extension()

    def cleanup(self):
        """
        Called when the stage is closed or the extension is hot reloaded.
        Perform any necessary cleanup such as removing active callback functions
        Buttons imported from isaacsim.gui.components.element_wrappers implement a cleanup function that should be called
        """
        for ui_elem in self.wrapped_ui_elements:
            ui_elem.cleanup()

    def build_ui(self):
        """
        Build a custom UI tool to run your extension.
        This function will be called any time the UI window is closed and reopened.
        """
        world_controls_frame = CollapsableFrame("World Controls", collapsed=False)

        with world_controls_frame:
            with ui.VStack(style=get_style(), spacing=5, height=0):
                self._load_btn = LoadButton(
                    "Load Button", "LOAD", setup_scene_fn=self._setup_scene, setup_post_load_fn=self._setup_scenario
                )
                self._load_btn.set_world_settings(physics_dt=1 / 60.0, rendering_dt=1 / 60.0)
                self.wrapped_ui_elements.append(self._load_btn)

                self._reset_btn = ResetButton(
                    "Reset Button", "RESET", pre_reset_fn=None, post_reset_fn=self._on_post_reset_btn
                )
                self._reset_btn.enabled = False
                self.wrapped_ui_elements.append(self._reset_btn)

        run_scenario_frame = CollapsableFrame("Run Scenario")

        with run_scenario_frame:
            with ui.VStack(style=get_style(), spacing=5, height=0):
                self._scenario_state_btn = StateButton(
                    "Run Scenario",
                    "RUN",
                    "STOP",
                    on_a_click_fn=self._on_run_scenario_a_text,
                    on_b_click_fn=self._on_run_scenario_b_text,
                    physics_callback_fn=self._update_scenario,
                )
                self._scenario_state_btn.enabled = False
                self.wrapped_ui_elements.append(self._scenario_state_btn)

        with ui.VStack(style=get_style(), spacing=5, height=0):
            ui.Button("Debug Button", height=20, clicked_fn=self._get_grid_points)
            ui.Button("Generate Spheres", height=20, clicked_fn=self._generate_spheres)

    ######################################################################################
    # Functions Below This Point Support The Provided Example And Can Be Deleted/Replaced
    ######################################################################################

    def _on_init(self):
        self._articulation = None
        self._cuboid = None
        self._scenario = FrankaRmpFlowExampleScript()

    def _add_light_to_stage(self):
        """
        A new stage does not have a light by default.  This function creates a spherical light
        """
        sphereLight = UsdLux.SphereLight.Define(get_current_stage(), Sdf.Path("/World/SphereLight"))
        sphereLight.CreateRadiusAttr(2)
        sphereLight.CreateIntensityAttr(100000)
        SingleXFormPrim(str(sphereLight.GetPath())).set_world_pose([6.5, 0, 12])

    def _setup_scene(self):
        """
        This function is attached to the Load Button as the setup_scene_fn callback.
        On pressing the Load Button, a new instance of World() is created and then this function is called.
        The user should now load their assets onto the stage and add them to the World Scene.
        """
        create_new_stage()
        self._add_light_to_stage()

        loaded_objects = self._scenario.load_example_assets()

        # Add user-loaded objects to the World
        world = World.instance()
        for loaded_object in loaded_objects:
            world.scene.add(loaded_object)

    def _setup_scenario(self):
        """
        This function is attached to the Load Button as the setup_post_load_fn callback.
        The user may assume that their assets have been loaded by their setup_scene_fn callback, that
        their objects are properly initialized, and that the timeline is paused on timestep 0.
        """
        self._scenario.setup()

        # UI management
        self._scenario_state_btn.reset()
        self._scenario_state_btn.enabled = True
        self._reset_btn.enabled = True

    def _on_post_reset_btn(self):
        """
        This function is attached to the Reset Button as the post_reset_fn callback.
        The user may assume that their objects are properly initialized, and that the timeline is paused on timestep 0.

        They may also assume that objects that were added to the World.Scene have been moved to their default positions.
        I.e. the cube prim will move back to the position it was in when it was created in self._setup_scene().
        """
        self._scenario.reset()

        # UI management
        self._scenario_state_btn.reset()
        self._scenario_state_btn.enabled = True

    def _update_scenario(self, step: float):
        """This function is attached to the Run Scenario StateButton.
        This function was passed in as the physics_callback_fn argument.
        This means that when the a_text "RUN" is pressed, a subscription is made to call this function on every physics step.
        When the b_text "STOP" is pressed, the physics callback is removed.

        This function will repeatedly advance the script in scenario.py until it is finished.

        Args:
            step (float): The dt of the current physics step
        """
        done = self._scenario.update(step)
        if done:
            self._scenario_state_btn.enabled = False

    def _on_run_scenario_a_text(self):
        """
        This function is attached to the Run Scenario StateButton.
        This function was passed in as the on_a_click_fn argument.
        It is called when the StateButton is clicked while saying a_text "RUN".

        This function simply plays the timeline, which means that physics steps will start happening.  After the world is loaded or reset,
        the timeline is paused, which means that no physics steps will occur until the user makes it play either programmatically or
        through the left-hand UI toolbar.
        """
        self._timeline.play()

    def _on_run_scenario_b_text(self):
        """
        This function is attached to the Run Scenario StateButton.
        This function was passed in as the on_b_click_fn argument.
        It is called when the StateButton is clicked while saying a_text "STOP"

        Pausing the timeline on b_text is not strictly necessary for this example to run.
        Clicking "STOP" will cancel the physics subscription that updates the scenario, which means that
        the robot will stop getting new commands and the cube will stop updating without needing to
        pause at all.  The reason that the timeline is paused here is to prevent the robot being carried
        forward by momentum for a few frames after the physics subscription is canceled.  Pausing here makes
        this example prettier, but if curious, the user should observe what happens when this line is removed.
        """
        self._timeline.pause()

    def _reset_extension(self):
        """This is called when the user opens a new stage from self.on_stage_event().
        All state should be reset.
        """
        self._on_init()
        self._reset_ui()

    def _reset_ui(self):
        self._scenario_state_btn.reset()
        self._scenario_state_btn.enabled = False
        self._reset_btn.enabled = False

    ############################################ new functions ############################################

    def _get_grid_points(self):
        import numpy as np
        import cv2
        import os

        image_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "../data", "sample_weld_gun2.png")

        gray_img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
        if gray_img is None:
            print(f"Error: Could not read image at {image_path}")
            return

        print("max value", np.max(gray_img))
        print("min value", np.min(gray_img))
        
        # turn gray_img into a binary image
        # _, binary_img = cv2.threshold(gray_img, 100, 255, cv2.THRESH_BINARY)
        binary_img = (gray_img > 200).astype(int)

        print("max value", np.max(binary_img))
        print("min value", np.min(binary_img))

        # save binary_img
        cv2.imwrite(os.path.join(os.path.dirname(os.path.abspath(__file__)), "../data", "binary_img.png"), binary_img * 255)
        
        print("Image converted to grayscale")
        print(f"Grayscale image shape: {gray_img.shape}")  # Should be (height, width) instead of (height, width, 3)

        # Get height and width
        height, width = gray_img.shape[:2]
        print(f"Image resolution: {width}x{height} pixels")

        # radius of sphere
        radius = 10 # in pixels
        thredhold = 50
        
        # Generate grid points
        # Calculate number of points that can fit in width and height
        num_points_x = width // (2 * radius)
        num_points_y = height // (2 * radius)
        
        # Generate x and y coordinates for grid points
        x_coords = np.arange(radius, width - radius, 2 * radius)
        y_coords = np.arange(radius, height - radius, 2 * radius)
        
        # Create meshgrid of coordinates
        X, Y = np.meshgrid(x_coords, y_coords)
        
        # Reshape to get list of (x,y) coordinates
        grid_points = np.column_stack((X.ravel(), Y.ravel()))
        
        # Calculate sum of pixels inside circles
        sphere_points = []
        for point in grid_points:
            x, y = point
            # Create a circular mask
            y_grid, x_grid = np.ogrid[:height, :width]
            dist_from_center = np.sqrt((x_grid - x)**2 + (y_grid - y)**2)
            mask = dist_from_center <= radius
            
            # Calculate sum of pixels inside the circle
            circle_sum = np.sum(binary_img[mask])
            if circle_sum < 3.14 * radius * radius - thredhold:
                print("circle_sum", circle_sum)
                sphere_points.append([x, y])

        print("sphere_points", sphere_points)
        
        # Create a copy of the original image for drawing
        visualization_img = cv2.imread(image_path)
        
        # Draw circles at sphere points
        for point in sphere_points:
            x, y = int(point[0]), int(point[1])
            # Draw circle: (image, center, radius, color, thickness)
            cv2.circle(visualization_img, (x, y), radius, (0, 255, 0), 2)  # Green circles with thickness 2
        
        # Save the visualization
        output_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "../data", "sphere_points_visualization.png")
        cv2.imwrite(output_path, visualization_img)
        print(f"Visualization saved to: {output_path}")

        return [[e[0] - width / 2, height / 2 - e[1]] for e in sphere_points], radius
        
    def _generate_spheres(self):
        import os
        from pxr import UsdGeom, Usd
        stage =  omni.usd.get_context().get_stage()
        asset_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "../data", "sample_weld_gun2.usd")
        # Create an xform which should hold all payloads in this sample
        prim: Usd.Prim = UsdGeom.Xform.Define(stage, Sdf.Path("/World/sample")).GetPrim()
        prim.GetReferences().AddReference(asset_path)
        # # prim.GetAttribute("xformOp:translate").Set((-0.5, 0.5, 0.0))

        print("Generating sphere for a mesh")
        from .sphere_editor import SphereEditor
        sphere_editor = SphereEditor()

        scale = 20.0

        sphere_points, radius = self._get_grid_points()
        print("\n\n ===? sphere_points", sphere_points)
        sphere_points = [e for e in sphere_points]
        sphere_group = UsdGeom.Xform.Define(stage, Sdf.Path("/World/spheres")).GetPrim()
        UsdGeom.Xformable(sphere_group).AddTransformOp()
        for point in sphere_points:
            center = [0, point[0] / scale, point[1] / scale]
            sphere_editor.add_sphere("/World/spheres", center, radius / scale)
        
        return