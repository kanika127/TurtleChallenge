# TurtleChallenge

This project presents a solution to the Turtle Segmentation Challenge, focusing on building a deep learning model capable of segmenting turtles in synthetic images. The challenge comprises developing a model for semantic segmentation, and implementing geometric algorithms to process the model's predictions.

## Overview
The goal is to accurately segment turtles in a test image using a deep learning model and then apply geometric algorithms to the segmentation mask. This involves:
> 1. Developing a model for semantic segmentation to distinguish between the turtle (foreground) and everything else (background).
> 2. Implementing algorithms to find a convex hull enclosing the turtle pixels and calculating the area of this polygon.

## Dataset
### Training Data: 
Consists of 30 256x256 images of a synthetic turtle pasted on artificially generated background images by BigGAN. Each image comes with the ground truth per-pixel segmentation mask.
### Test Data: 
A single test image of resolution 512x512 without a ground truth segmentation mask.

## Tasks
Semantic Segmentation: Develop a deep learning model to accurately segment the turtle in the test image.
### Convex Hull Calculation: 
Implement an algorithm to find a convex hull enclosing all foreground (turtle) pixels based on the model's prediction.
### Area Calculation (Bonus): 
Implement an algorithm to calculate the area of the convex hull polygon.

## Implementation Details
### Model: 
The solution utilizes a U-Net architecture for semantic segmentation, trained on the provided synthetic dataset.
### Geometric Algorithms: 
Custom algorithms were developed for calculating the convex hull and the area of the convex hull without relying on high-level image processing libraries like cv2 or scikit-image.
