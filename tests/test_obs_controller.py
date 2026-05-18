import unittest
from src.obs_controller import OBSController

class TestOBSController(unittest.TestCase):

    def setUp(self):
        self.obs_controller = OBSController()

    def test_transition_scene(self):
        # Assuming 'Scene1' is a valid scene name in OBS
        result = self.obs_controller.transition_scene('Scene1')
        self.assertTrue(result)

    def test_get_current_scene(self):
        # Assuming the current scene is 'Scene1'
        current_scene = self.obs_controller.get_current_scene()
        self.assertEqual(current_scene, 'Scene1')

if __name__ == '__main__':
    unittest.main()