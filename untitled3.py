# -*- coding: utf-8 -*-
"""Untitled3.ipynb

Automatically generated by Colab.

Original file is located at
    https://colab.research.google.com/drive/14qTyyuqjIWIZQP5qG97pfvIi0EcDwHIo
"""

import os
import tarfile
import torch
import torchvision
from torchvision.transforms import functional as F
from PIL import Image
import json
import pandas as pd
import pandas as pd

# Google Colab specific code to use data from Google Drive
from google.colab import drive
drive.mount('/content/drive')

# Extract the dataset from the provided location
dataset_path = '/content/drive/MyDrive/cub/CUB_200_2011.tgz'
extract_path = '/content/cub_dataset'

if not os.path.exists(extract_path):
    with tarfile.open(dataset_path, 'r:gz') as tar:
        tar.extractall(path=extract_path)

# Dataset path adjustment
images_path = os.path.join(extract_path, 'CUB_200_2011', 'images')
# Removed unused annotations path

# Custom Dataset Class for Faster R-CNN
class CustomDataset(torch.utils.data.Dataset):
    def __init__(self, root, transforms=None):
        self.root = root
        self.transforms = transforms
        self.imgs = list(sorted(os.listdir(os.path.join(root, "CUB_200_2011", "images"))))
        images = pd.read_csv(os.path.join(root, 'CUB_200_2011', 'images.txt'), sep=" ", names=["img_id", "filepath"])
        bboxes = pd.read_csv(os.path.join(root, 'CUB_200_2011', 'bounding_boxes.txt'), sep=" ", names=["img_id", "x", "y", "width", "height"])
        labels = pd.read_csv(os.path.join(root, 'CUB_200_2011', 'image_class_labels.txt'), sep=" ", names=["img_id", "class_id"])
        split = pd.read_csv(os.path.join(root, 'CUB_200_2011', 'train_test_split.txt'), sep=" ", names=["img_id", "is_train"])
        self.metadata = images.merge(bboxes, on="img_id").merge(labels, on="img_id").merge(split, on="img_id")

    def __getitem__(self, idx):
        data = self.metadata.iloc[idx]
        img_path = os.path.join(self.root, 'CUB_200_2011', 'images', data['filepath'])
        data = self.metadata.iloc[idx]
        img_path = os.path.join(self.root, 'CUB_200_2011', 'images', data['filepath'])
        image = Image.open(img_path).convert("RGB")

        x, y, width, height = data['x'], data['y'], data['width'], data['height']
        boxes = torch.tensor([[x, y, x + width, y + height]], dtype=torch.float32)
        labels = torch.tensor([data['class_id'] - 1], dtype=torch.int64)

        mask = torch.zeros((1, int(image.height), int(image.width)), dtype=torch.uint8)
        target = {"boxes": boxes, "labels": labels, "masks": mask}



        if self.transforms:
            image = self.transforms(image)

        return image, target

    def __len__(self):
        return len(self.imgs)

# Define the transforms and dataset
dataset = CustomDataset(root=extract_path, transforms=torchvision.transforms.ToTensor())
data_loader = torch.utils.data.DataLoader(dataset, batch_size=2, shuffle=True, num_workers=4, collate_fn=lambda x: tuple(zip(*x)))

# Load the pre-trained Faster R-CNN model
model = torchvision.models.detection.fasterrcnn_resnet50_fpn(pretrained=True)

# Update the classifier head
num_classes = 201  # Update with the number of classes including background
in_features = model.roi_heads.box_predictor.cls_score.in_features
model.roi_heads.box_predictor = torchvision.models.detection.faster_rcnn.FastRCNNPredictor(in_features, num_classes)

# Set the device
device = torch.device('cuda') if torch.cuda.is_available() else torch.device('cpu')
model.to(device)

# Optimizer setup
params = [p for p in model.parameters() if p.requires_grad]
optimizer = torch.optim.SGD(params, lr=0.005, momentum=0.9, weight_decay=0.0005)

# Training loop
num_epochs = 10
for epoch in range(num_epochs):
    model.train()
    i = 0
    for images, targets in data_loader:
        images = list(image.to(device) for image in images)
        targets = [{k: v.to(device) for k, v in t.items()} for t in targets]

        # Calculate loss
        loss_dict = model(images, targets)
        losses = sum(loss for loss in loss_dict.values())

        # Backpropagation
        optimizer.zero_grad()
        losses.backward()
        optimizer.step()

        i += 1
        print(f"Epoch [{epoch + 1}/{num_epochs}], Step [{i}/{len(data_loader)}], Loss: {losses.item():.4f}")

print("Training completed!")