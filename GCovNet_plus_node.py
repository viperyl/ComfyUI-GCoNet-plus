import os

import torch
import torch.nn as nn
from torchvision import transforms

from .gconet_plus_models.GCoNet_plus import GCoNet_plus
from .gconet_plus_models.GCovNet_plus_config import Config

from loguru import logger
from glob import glob
from folder_paths import models_dir
from PIL import Image
import numpy as np

config = Config()


class GCovNet_img_processor:
    def __init__(self, image_size):
        self.data_size = (image_size, image_size)
        self.transform_image = transforms.Compose([
            transforms.Resize(self.data_size),
            transforms.ToTensor(),
            transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
        ])

    def __call__(self, _image: torch.tensor):
        _image = Image.fromarray(np.uint8(_image*255)).convert('RGB')
        _image = self.transform_image(_image)
        return _image
    
class GCovNet_plus_node:
    def __init__(self):
        self.ready = False
        self.checkpoints = None
        self.device = None

    def load(self, device, checkpoints, verbose=False):
        self.model = GCoNet_plus()
        gconet_dict = torch.load(os.path.join(models_dir, "GCoNet_plus_checkpoints", checkpoints))
        self.model.to(device)
        self.model.load_state_dict(gconet_dict)
        self.model.eval()
        
        self.img_processor = GCovNet_img_processor(224)

        self.ready = True
        self.checkpoints = checkpoints
        self.device = device


    
    @classmethod
    def INPUT_TYPES(s):
        if torch.backends.mps.is_available():
            mps_device = ["mps"]
        else:
            mps_device = []
        
        if torch.cuda.is_available():
            cuda_deviceds = [f"cuda:{i}" for i in range(torch.cuda.device_count())]
        else:
            []

        checkpoints = [os.path.basename(item) for item in glob(os.path.join(models_dir, "GCoNet_plus", "*"))]

        return {
            "required": {
                "device": (["auto", "cpu"] + cuda_deviceds + mps_device, {"default": "auto"}),
                "checkpoints": (checkpoints, {"default": checkpoints[0]}),
                "image": ("IMAGE", {}),
            }
        }
    
    RETURN_TYPES = ("MASK", )
    RETURN_NAMES = ("mask", )
    FUNCTION = "salient_object_detection"
    CATEGORY = "Fooocus"
    
    def salient_object_detection(self, device, checkpoints, image):
        if self.device != device or self.checkpoints != checkpoints:
            self.load(device, checkpoints)
        
        image = image.squeeze().numpy()
        inputs = self.img_processor(image)[None, ...]
        with torch.no_grad():
            inputs = inputs.to(self.device)
            scaled_preds = self.model(inputs)[-1]

        res = nn.functional.interpolate(scaled_preds, size=image.shape[:2], mode='bilinear', align_corners=True)

        return res





NODE_CLASS_MAPPINGS = {
    "GCovNetPlus": GCovNet_plus_node,
}

# A dictionary that contains the friendly/humanly readable titles for the nodes
NODE_DISPLAY_NAME_MAPPINGS = {
    "GCovNetPlus": "GCovNetPlus",
}



