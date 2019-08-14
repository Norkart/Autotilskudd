# -*- coding: utf-8 -*-
"""
Created on Wed Mar 27 10:18:49 2019

@author: runaas
"""

import os
import gdal
import numpy as np
import matplotlib as mpl
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import sklearn.mixture as mix
import training_data

def plot_ellipses(ax, weights, means, covars):
    for n in range(means.shape[0]):
        eig_vals, eig_vecs = np.linalg.eigh(covars[n])
        unit_eig_vec = eig_vecs[0] / np.linalg.norm(eig_vecs[0])
        angle = np.arctan2(unit_eig_vec[1], unit_eig_vec[0])
        # Ellipse needs degrees
        angle = 180 * angle / np.pi
        # eigenvector normalization
        eig_vals = 2 * np.sqrt(2) * np.sqrt(eig_vals)
        ell = mpl.patches.Ellipse(means[n], eig_vals[0], eig_vals[1],
                                  180 + angle, edgecolor='black')
        ell.set_clip_box(ax.bbox)
        ell.set_alpha(weights[n])
        ell.set_facecolor('#56B4E9')
        ax.add_artist(ell)


def plot_results(ax, X, estimator, title, plot_title=False):
    ax.set_title(title)
    # ax1.scatter(X[:, 0], X[:, 1], s=5, marker='o', color=colors[y], alpha=0.8)
    maxval = X.max()
    minval = X.min()
    ax.set_xlim(minval, maxval)
    ax.set_ylim(minval, maxval)
    ax.set_xticks(())
    ax.set_yticks(())
    plot_ellipses(ax, estimator.weights_, estimator.means_,
                  estimator.covariances_)

    if plot_title:
        ax.set_ylabel('Estimated Mixtures')


#for i in range(gdal.GetDriverCount()):
#    driver = gdal.GetDriver(i)
#    name = driver.GetDescription()
#    if name.find("JP") >= 0:
#        print(name)

def gmm_cluster():
    data_path = "C:\\Users\\runaas.NORKART\\PycharmProjects\\SentinelTest\\data"
    img_dir_path = os.path.join(data_path, "S2B_MSIL2A_20180821T104019_N0208_R008_T32VNM_20180821T170337\\S2B_MSIL2A_20180821T104019_N0208_R008_T32VNM_20180821T170337.SAFE\\GRANULE\\L2A_T32VNM_A007613_20180821T104015\\IMG_DATA\\R10m")
    image_names = [
            "T32VNM_20180821T104019_B02_10m.jp2",
            "T32VNM_20180821T104019_B03_10m.jp2",
            "T32VNM_20180821T104019_B04_10m.jp2",
            "T32VNM_20180821T104019_B08_10m.jp2"
            ]

    np_bands, cols, rows, xform, proj = training_data.image_set_load(img_dir_path, image_names)

    X = np.concatenate([b.reshape((b.shape[0]*b.shape[1], 1)) for b in np_bands], axis=1)

    cut = X[[1,3,4], :]

    title = "Diriclet prior"

    gmm = mix.BayesianGaussianMixture(n_components=10,
                                      reg_covar=0, init_params='random',
                                      max_iter=1500, mean_precision_prior=.8)
    gmm.fit(X[np.random.choice(X.shape[0], 50000), :])
    prediction = gmm.predict(X)
    prediction = prediction.reshape(np_bands[0].shape)
    prediction = np.array(prediction, dtype=np.ubyte)

    # Save result
    tiff_driver = gdal.GetDriverByName('GTiff')
    out_fn = os.path.join(img_dir_path, "clustered.tif")
    outRaster = tiff_driver.Create(out_fn, prediction.shape[0], prediction.shape[1], 1, gdal.GDT_Byte)
    outRaster.SetGeoTransform(xform)
    outRaster.SetProjection(proj)
    outRaster.GetRasterBand(1).WriteArray(prediction)
    outRaster.FlushCache()

    plt.figure(figsize=(4.7 * 3, 8))
    plt.subplots_adjust(bottom=.04, top=0.90, hspace=.05, wspace=.05,
                        left=.03, right=.99)

    gs = gridspec.GridSpec(2, 3)


    for k in range(3):
        plot_results(plt.subplot(gs[0:2, k]), X[:, k:k+2], gmm,
                     r"%s$%d$%d" % (title, k, k+1),
                     plot_title=(k == 0))

    plt.show()

    #np_image = np.concatenate([b.reshape(b.shape + (1,)) for b in np_bands], axis=2)

    #print(np_image.shape)

    #fig = plt.figure()
    #ax = fig.add_subplot(111, projection='3d')

    #ax.scatter(np_bands[0].flatten()[::10000],
    #           np_bands[1].flatten()[::10000],
    #           np_bands[2].flatten()[::10000],
    #           c='r', marker='o')

    #ax.set_xlabel('R Label')
    #ax.set_ylabel('G Label')
    #ax.set_zlabel('B Label')

    # plt.show()
