# -*- coding: utf-8 -*-
"""[Kanika Agarwal] DeepLearning_TurtleChallenge.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1Wunx7ZWRnGWW-cUnqhW4_jgs9D851IkF

# Introduction

*In this challenge you will be asked to build a deep learning solution capable of segmenting turtles on synthetic images. You will be provided with the data, which you can use to train your models; your best model will be used on a test image and you will be asked to implement some geometric algorithms based on the predictions of your model.*

***Training data***

The training data will consist of 30 256x256 images of the same synthetic turtle pasted on background images artificially generated by BigGAN (https://arxiv.org/abs/1809.11096).

Feel free to increase the dataset size as needed and make any relevant changes to the dataset creation.

Each image will come with the ground truth per-pixel segmentation mask which you can leverage for your training setup. We strongly recommend that you treat the provided task as semantic segmentation with 2 classes -- foreground (turtle) and background (everything else).

You are also allowed to use external data sources and pre-trained weights, but please provide justification if you choose to do so.


***Test data***

There will only be a single test image without the provided GT.

The test image differs from the training data and it is up to you to decide how to approach these differences. Notably, the test image is of resolution 512x512 and your predicted mask must be of the same resolution.


***Tasks***

1. Your main task is to build a deep learning model capable of accurately segmenting the turtle in the test image.
2. Based on the segmentation mask predicted by your model, you will need to implement an algorithm that finds a convex hull, i.e. a polygon enclosing all the foreground (i.e. turtle) pixels.
3. [Bonus Points] Implement an algorithm that calculates the area of the polygon from the result of task 2.

***If you are using third-party code, you have to provide explanation of why you need that code and what that code does. We evaluate your submission based on the code you have written and if there is no such code, we won't be able to evaluate and proceed to the next stage.***

***Rules***

* While we provide all the code in PyTorch, feel free to use other deep learning frameworks as needed
* Feel free to use all the imported Python libraries
* For tasks 2 and 3 ***you are not allowed*** to use third-party functions that readily solve those tasks, e.g. you are not allowed to use various `cv2` and `scikit-image` operators. We expect the algorithms to be based on points and geometry rather than full-image operations.


***Submission***

* ***You must send us only a single link to the Colab notebook with your solution and nothing else!*** We should be able to reproduce your results by running the notebook. If you require additional files, use `gdown` to download them into the session storage (see Task 1 for details).
* Include your comments and explanations on the decisions that you made to approach the problem;
* Make sure to include the estimate of approximately how much time it took you to get to the final solution.

***Colab setup***

* To use GPU, go to `Runtime -> Change Runtime Type -> GPU`
"""

# Commented out IPython magic to ensure Python compatibility.
# comment the following line if you are working outside of a notebook environment
# %matplotlib inline
import matplotlib.pyplot as plt
import numpy as np
import random
from PIL import Image

# Used to download any files you need for your solution from Google Drive
import gdown
gdown.download("https://drive.google.com/uc?id=1ymKI8M73kBIck2b7S7QG02aiP4yXLaML", "turtle.png", quiet=False)



# read and visualise the turtle image
turtle_image = Image.open('./turtle.png')
# it is a 4-channel RGB+Alpha image of size 2394x1800
print(turtle_image.mode, turtle_image.size)

turtle_image

# to create the training set, we will resize the turtle image to 256x256
turtle_image_256x256 = turtle_image.resize((256, 256))

"""# Background Images

As written above, we will use a generative adversarial network called "BigGAN" pre-trained on ImageNet to create a set of background images
"""

# first, we need to install the python package called `pytorch_pretrained_biggan` (https://github.com/huggingface/pytorch-pretrained-BigGAN)
# if in the notebook environment, please uncomment the following line to install this package
!pip install pytorch_pretrained_biggan
# there might be some errors related to pip's dependency resolver which you can safely ignore

import torch
from pytorch_pretrained_biggan import (
    BigGAN,
    truncated_noise_sample,
    convert_to_images,
    one_hot_from_int,
)

device = torch.device("cuda") if torch.cuda.is_available() else torch.device("cpu")
# boilerplate pytorch code enforcing reproducibility
torch.manual_seed(42)
if device.type == "cuda":
    torch.cuda.manual_seed(42)
np.random.seed(42)
random.seed(42)

"""BigGAN is a memory-intensive network.

To save time and memory, we will only generate 30 different background images.
Feel free to change this setup as needed.
"""

## NOTE: This section can be skipped to save time - Only used for training
# Using 30000 backgroung images as opposed to 30

# load the 256x256 model
model = BigGAN.from_pretrained('biggan-deep-256').to(device).eval()

# every time we will run with batch size of 3 in order to not run out of memory
num_passes = 10000 # using 30000 instead of 30 training images
batch_size = 3

# default noise value from the provided repository
truncation = 0.4

background_images = []

for _ in range(num_passes):
    # BigGAN uses imagenet and hence each time we will choose one of 1000 categories
    class_vector = torch.from_numpy(
        one_hot_from_int(np.random.randint(0, 1000, size=batch_size), batch_size=batch_size)
    ).to(device)
    noise_vector = torch.from_numpy(
        truncated_noise_sample(truncation=truncation, batch_size=batch_size)
    ).to(device)

    # Generate the images and convert them to PIL image
    with torch.no_grad():
        output = model(noise_vector, class_vector, truncation).cpu()
        background_images.extend(convert_to_images(output))

# We won't need the GAN model anymore,
# so we can safely delete it and free up some memory
del model
torch.cuda.empty_cache()

## NOTE: This section can be skipped to save time - Only used for training

# Let's see how one of the images look like
random.choice(background_images)

"""# Training Set
Given 30 background images and the turtle image, we will paste the turtle onto the background images.
"""

import torchvision
import torchvision.transforms as transforms

tensor_transform = transforms.ToTensor()

# Adding random rotate and flip

def random_paste(background_image, turtle_image, min_scale=0.25, max_scale=0.65):
    """Randomly scales and pastes the turtle image onto the background image"""
    if random.randint(0, 2):
        turtle_image = turtle_image.transpose(Image.FLIP_LEFT_RIGHT)
    w, h = turtle_image.size
    # first, we will randomly downscale the turtle image
    new_w = int(random.uniform(min_scale, max_scale) * w)
    new_h = int(random.uniform(min_scale, max_scale) * h)
    angle = random.uniform(0, 360)
    resized_turtle_image = turtle_image.resize((new_w, new_h)).rotate(angle)

    # second, will randomly choose the locations where to paste the new image
    start_w = random.randint(0, w - new_w)
    start_h = random.randint(0, h - new_h)

    # third, will create the blank canvas of the same size as the original image
    canvas_image = Image.new('RGBA', (w, h))

    # and paste the resized turtle onto it, preserving the mask
    canvas_image.paste(resized_turtle_image, (start_w, start_h), resized_turtle_image)

    # Turtle image is of mode RGBA, while background image is of mode RGB;
    # `.paste` requires both of them to be of the same type.
    angle = random.uniform(0, 360)
    background_image = background_image.rotate(angle)
    background_image = background_image.copy().convert('RGBA')
    # finally, will paste the resized turtle onto the background image
    background_image.paste(resized_turtle_image, (start_w, start_h), resized_turtle_image)
    return background_image, canvas_image

## NOTE: This section can be skipped to save time - Only used for training

training_set = []  # image, segmentation mask

for background_image in background_images:
  # paste the turtle onto background image
  aug_image, aug_mask = random_paste(background_image.copy(), turtle_image_256x256.copy())
  # convert PIL images to pytorch tensors
  training_pair = [
      tensor_transform(aug_image)[:3],  # keep the rgb only
      # For the mask, we only need the last (4th) channel,
      # and we will encode the mask as boolean
      tensor_transform(aug_mask)[-1:] > 0,
  ]
  training_set.append(training_pair)

## NOTE: This section can be skipped to save time - Only used for training

# Let's visualise some subset of the training set
sample_indices = np.random.choice(len(training_set), size=9, replace=False)
sample_images = []
sample_masks = []
for i in sample_indices:
    image, mask = training_set[i]
    sample_images.append(image)
    sample_masks.append(mask)

plt.figure(figsize=(18, 18))
plt.subplot(121)
plt.imshow(torchvision.utils.make_grid(sample_images, nrow=3).permute(1, 2, 0).cpu().numpy())
plt.subplot(122)
plt.imshow(torchvision.utils.make_grid(sample_masks, nrow=3).permute(1, 2, 0).float().cpu().numpy())

"""# Test Image
Now, let's load the test image. As mentioned above, it is of a slightly higher 512x512 resolution.
"""

gdown.download("https://drive.google.com/uc?id=1_55KX8AK8pZ936Zv27t8Q-ZY8BJjuBqa", "test.png", quiet=False)
test_image = Image.open('./test.png')
# it is a 3-channel RGB image of size 512x512
print(test_image.mode, test_image.size)
test_image

"""# Task 1: Predicting segmentation mask

*This is where you need to implement your deep learning solution. Your approach should output a result at the native 512x512 resolution of the test image.*
"""

# import torch modules

from torch.nn import Conv2d, ConvTranspose2d, MaxPool2d, ReLU
from torch.nn import Module, ModuleList
from torch.nn import functional as F
from torch.nn import BCEWithLogitsLoss
from torch.optim import Adam
from torchvision.transforms import CenterCrop
from torch.utils.data import DataLoader, Dataset

# Dataset

class TurtleDataset(Dataset):
    def __init__(self, dataset):
        self.images = [x[0] for x in dataset]
        self.masks = [x[1] for x in dataset]

    def __getitem__(self, idx):
        img = self.images[idx]
        mask = self.masks[idx]
        return img, mask.float()

    def __len__(self):
        return len(self.images)

## NOTE: This section can be skipped to save time - Only used for training

train_dataset = TurtleDataset(training_set)

train_loader = DataLoader(train_dataset, batch_size=16, shuffle=True, num_workers=8)

# U-Net Model

class ConvModule(Module):
  def __init__(self, c_in, c_out):
    super().__init__()
    self.conv1 = Conv2d(c_in, c_out, 3)
    self.conv2 = Conv2d(c_out, c_out, 3)
    self.relu = ReLU()

  def forward(self, x):
    return self.conv2(self.relu(self.conv1(x)))


class Encoder(Module):
	def __init__(self):
		super().__init__()
		self.encoding_modules = ModuleList(
			[ConvModule(3, 16), ConvModule(16, 32), ConvModule(32, 64)]
    )
		self.maxpool = MaxPool2d(2)

	def forward(self, x):
		output = []
		for module in self.encoding_modules:
			x = module(x)
			output.append(x)
			x = self.maxpool(x)
		return output


class Decoder(Module):
	def __init__(self):
		super().__init__()
		self.upsampling_modules = ModuleList(
			[ConvTranspose2d(64, 32, 2, 2), ConvTranspose2d(32, 16, 2, 2)]
    )
		self.decoding_modules = ModuleList(
			[ConvModule(64, 32), ConvModule(32, 16)]
    )

	def forward(self, x, f):
		for idx, upsampling_module in enumerate(self.upsampling_modules):
			x = upsampling_module(x)
			cropped_f = CenterCrop(x.shape[-2:])(f[idx])
			x = torch.cat([x, cropped_f], dim=1)
			x = self.decoding_modules[idx](x)
		return x



class UNet(Module):
  def __init__(self):
    super().__init__()
    self.encoder = Encoder()
    self.decoder = Decoder()
    self.final_layer = Conv2d(16, 1, 1)

  def forward(self, x, outSize=(256, 256)):
    e = self.encoder(x)
    d = self.decoder(e[::-1][0], e[::-1][1:])
    return F.interpolate(self.final_layer(d), outSize)

unet = UNet().to(device)

## NOTE: Mentioned about this section later during inference

from google.colab import drive
drive.mount('/content/gdrive')

model_save_location = '/content/gdrive/MyDrive/TurtleSegmentation'

num_epochs = 40

## NOTE: This section can be skipped to save time - Only used for training

# TODO: Implement and train the deep model

from tqdm import tqdm

lossFunc = BCEWithLogitsLoss()
opt = Adam(unet.parameters(), lr=1e-4)

for epoch in tqdm(range(num_epochs)):
  unet.train()
  train_loss = 0
  for idx, (x, y) in enumerate(train_loader):
    (x, y) = (x.to(device), y.to(device))
    pred = unet(x)
    loss = lossFunc(pred, y)
    opt.zero_grad()
    loss.backward()
    opt.step()
    train_loss += loss
  train_loss /= len(train_loader)
  print("EPOCH: {}\tLOSS: {:.6f}".format(epoch + 1, train_loss))
  # TODO: Save the model weights and upload them to Google Drive
  torch.save(unet, f'{model_save_location}/checkpoint{epoch}.pth')

## PLEASE NOTE:
    #
    # Loading from the checkpoint after downloading using gdown is
    # resulting in a pickle error due to version mismatch. However, torch is
    # able to load successfully from my drive
    # i.e. '/content/gdrive/MyDrive/TurtleSegmentation'.
    #
    # In order to reproduce my run, please download the trained model
    # checkpoint (checkpoint36.pth) from saved_model_public_link
    # i.e. 'https://drive.google.com/drive/u/0/folders/14p-cYoHsxcWcce4gMPIUFGlvuZi1e3nj'
    # and upload to your own google drive.
    # Finally use the following lines with your g drive link to load
    #
    # from google.colab import drive
    # drive.mount('/content/gdrive')
    #
    # model_save_location = '/content/gdrive/MyDrive/TurtleSegmentation' (your folder)
    # unet = torch.load(model_save_location + '/checkpoint36.pth')

load_model_weights = True
if load_model_weights:
    # After uploading your saved model weights to Google Drive, share to
    # "Anyone with the link" and extract FILE_ID from the share link
    # See https://support.google.com/drive/answer/2494822?hl=en&co=GENIE.Platform%3DDesktop
    # for more information
    # Now the weights can be downloaded and used via gdown:
    # saved_model_url = "https://drive.google.com/uc?id=FILE_ID"
    # gdown.download(saved_model_url, "saved_model.pth", quiet=True)

    # TODO: Load your saved model weights e.g. torch.load("saved_model.pth")

    saved_model_public_link = 'https://drive.google.com/drive/u/0/folders/14p-cYoHsxcWcce4gMPIUFGlvuZi1e3nj'
    gdown.download(saved_model_public_link, "checkpoint36.pth", quiet=True)

    # unet = torch.load('checkpoint36.pth')

    ## PLEASE NOTE:
    #
    # Loading from the checkpoint after downloading using gdown is
    # resulting in a pickle error due to version mismatch. However, torch is
    # able to load successfully from my drive
    # i.e. '/content/gdrive/MyDrive/TurtleSegmentation'.
    #
    # In order to reproduce my run, please download the trained model
    # checkpoint (checkpoint36.pth) from saved_model_public_link
    # i.e. 'https://drive.google.com/drive/u/0/folders/14p-cYoHsxcWcce4gMPIUFGlvuZi1e3nj'
    # and upload to your own google drive.
    # Finally use the below line with your g drive link to load
    unet = torch.load(model_save_location + '/checkpoint36.pth')
    unet.eval()

test_image_tensor = tensor_transform(test_image)

def get_mask_from_image(test_image):
  # TODO: Use the deep model that predicts the segmentation mask on the test image
  # The model with the saved weights should be used, if load_model_weights is True
  # test_mask = test_image.mean(0) < 0.5
  test_mask = unet(test_image.to(device)[None], (512, 512))[0, 0] > 0.5
  return test_mask.byte()

test_mask_tensor = get_mask_from_image(test_image_tensor).cpu()

plt.figure(figsize=(12, 12))
plt.subplot(121)
plt.imshow(test_image_tensor.numpy().transpose(1, 2, 0))
plt.subplot(122)
plt.imshow(test_mask_tensor[:, :, None].numpy(), cmap="gray", vmin=0, vmax=1)

## NOTE: Only used for experimentation. This section can be skipped.

mask_img = []
for i in range(40):
  unet = torch.load(model_save_location + f"/checkpoint{i}.pth")
  unet.eval()
  mask_img.append(get_mask_from_image(test_image_tensor).cpu()[None, :, :])

plt.figure(figsize=(20, 20))
plt.imshow(torchvision.utils.make_grid(mask_img, nrow=8).permute(1, 2, 0).numpy()*255)

"""# Task 2: Calculating tight enclosing polygon from segmentation mask

*This is where you need to implement your algorithm that predicts a convex hull, an enclosing polygon of foreground pixels. You are not allowed to use cv2, scikit-image or other libraries' functionality that readily solve this task. Treat this problem as point-based rather than the image-based one.*

*You don't have to use PyTorch for this part. Your approach should output a result at the native 512x512 resolution of the test image.*

*For the purposes of this assignment, O(n^2) is considered a good time complexity*
"""

# This method is a comparator used to figure out which among y and z is a valid
# candidate to be chosen next after x to form a convex hull. It computes a
# dot-product of the two resulting vectors to compare their directions
def direction_comp(x, y, z):
  return (y[0] - x[0]) * (z[1] - y[1]) - (y[1] - x[1]) * (z[0] - y[0]) < 0

# Implemented Jarvis Gift Wrapping Algorithm that runs in O(nv) time where
# n is the number of points in the foreground and
# v is the number of vertices in the convex hull
def get_tight_polygon_from_mask(test_mask):
  # TODO: Implement an algorithm that computes the enclosing polygon from the segmentation mask.
  mask_points_n2 = torch.stack(torch.where(test_mask == 1), 1)
  polygon_points_n2 = []
  n = mask_points_n2.shape[0]

  # Find the left-most point
  left_most_idx = 0
  for i in range(1, n):
    if mask_points_n2[i, 1] < mask_points_n2[left_most_idx, 1]:
      left_most_idx = i
  x = left_most_idx

  # Keep on adding points in the convex hull until the starting point is reached
  while(True):
    polygon_points_n2.append(mask_points_n2[x])
    next_point = (x + 1) % n
    for i in range(n):
      # find the next point such that for any other point,
      # starting point to next point to any other point is clock-wise
      if(direction_comp(mask_points_n2[x], mask_points_n2[i], mask_points_n2[next_point])):
        next_point = i
    x = next_point
    if(x == left_most_idx):
      break

  return torch.stack(polygon_points_n2)

def visualize_polygon_on_image(test_image, polygon_points_n2):
  # append first point to close the figure
  polygon_points_n2 = torch.cat([polygon_points_n2, polygon_points_n2[:1]], 0)
  ys, xs = torch.split(polygon_points_n2, 1, dim=-1)
  plt.figure(figsize=(12, 12))
  plt.imshow(test_image.numpy().transpose(1, 2, 0))
  plt.plot(xs.numpy(), ys.numpy())

polygon_points_n2_tensor = get_tight_polygon_from_mask(test_mask_tensor)
visualize_polygon_on_image(test_image_tensor, polygon_points_n2_tensor)
visualize_polygon_on_image(test_mask_tensor[None], polygon_points_n2_tensor)

"""# Task 3 [bonus points]: Calculating the area of the polygon
*This is where you need to implement your area calculation algorithm. You are not allowed to use cv2, scikit-image or other libraries' functionality that readily solve this task. Once again, treat this problem as a point-based rather than the image-based one.*

*You don't have to use PyTorch for this part. Your approach should output a result at the native 512x512 resolution of the test image.*
"""

def area_triangle(p, q, r):
  return abs(p[0] * (q[1] - r[1]) + q[0] * (r[1] - p[1]) + r[0] * (p[1] - q[1])) / 2

def calculate_polygon_area(polygon_points_n2):
  # TODO: Implement the algorithm
  if polygon_points_n2.shape[0] < 3:
    return 0.0

  p = polygon_points_n2[-1]
  q = polygon_points_n2[0]
  r = polygon_points_n2[1]

  # Decompose convex hull with v vertices into v - 2 triangles
  # Add areas from v - 2 triangles to get the area of the convex hull
  return area_triangle(p, q, r) + calculate_polygon_area(polygon_points_n2[1:])

print("Area = {:.4f}".format(calculate_polygon_area(polygon_points_n2_tensor)))

# Area comes out as 24691.00 with the given test image, training checkpoint
# checkpoint36.pth and given random seeds

"""**Final Notes:**

Trained checkpoints and results are stored in the following public link:
https://drive.google.com/drive/folders/1jurJOv3ljUJF-YxZLlH1huB1Nt-bcXlA?usp=sharing

Segmentation results could have imporved with further training, improved dataset augmentation, and experimentation with other loss functions such as MSE. I only experimented with BCE loss.


The entire assignment took me around 5 hours to complete excluding model training time.

**Please Note:** In order to reproduce my run with my trained checkpoints, you would need to upload my trained checkpoint to your Google drive from the provided sharable link. I have explained some quick instructions in comments in the code segment above. Loading from the checkpoint after downloading using gdown results in a pickle error due to version mismatch.
"""
