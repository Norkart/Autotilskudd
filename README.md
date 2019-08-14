# Sentinel 2 CNN

Project for using machine learning for analysis of multispectral Sentinel 2 satellite images

## Getting Started

Clone this repository

### Prerequisites

This project requires Python, [TensorFlow](https://www.tensorflow.org/) and [GDAL](https://gdal.org/).
The author has used the [Anaconda](https://www.anaconda.com/) python distribution and installed TensorFlow
and GDAL trough the conda and conda-forge package repositories. [PyCharm](https://www.jetbrains.com/pycharm/)
is used as an IDE. The new [Anaconda enabled PyCharm](https://www.jetbrains.com/pycharm/promo/anaconda/) may
be more convenient than the standard version?

The [NVIDIA Cuda](https://developer.nvidia.com/cuda-zone) libraries has to be installed separately

### Installing

First install the newest NVIDIA drivers and the Cuda packages.

Install Anaconda Python and PyCharm.

It is recommended to install tensorflow in a separate conda environment

```
conda create -n tensorflow_gpuenv tensorflow-gpu
conda activate tensorflow_gpuenv
```

Currently the conda-forge version of GDAL must be used as it has Jpeg2000 support
(needed for loading Sentinel 2 images):

```
conda install -c conda-forge gdal
```

## Modules

**training_data.py** - cut the 100x100km satellite image tile (100000x100000 pixels) into training-friendly
tiles of 128x128 and 64x64 pixels, pack several channels into the same tiff file. Create feature images as training
targets. Assemble lists of suitable training - validation - test images.

**cnn.py** - Build a convolutional neural network and run training and test.

**cluster_test.py** and **senteniel_api.py** - experimental and unfinished code

## Authors

- **Rune Aasgaard** - _Initial work_
- Summer interns: Bjørn Magnus Valberg Iversen, Arild Dalsgård, and Erling Ljunggren
