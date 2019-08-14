# About satellite images and Senteniel 2

The human eye is capable of detecting electromagnetic radiation at wavelengths between 400-700nm, and separating this
range into three subintervals, usually known as the colours blue, green and red. We can use differences in absorption
and reflection of light to distinguish between various surfaces. However; natural materials like plants
and earth show great variation in reflectance also outside of the visible part of the spectrum.

Earth observation satellites utilize this by also having sensors in the infrared spectrum, around 700-2300nm.
This is still within the area of reflected solar radiation and should not be confused with thermal infrared in the
8-14 µ interval. Ultraviolet radiation is less useful as this part of the spectrum is heavily affected by
atmospheric scattering.

The Senteniel 2 multi-spectral instrument
([MSI](https://earth.esa.int/web/sentinel/user-guides/sentinel-2-msi/resolutions/radiometric))
has sensors for the three visual colors and a broadband infrared channel
with a ground resolution of 10m pr. pixel, and 6 narrowband IR sensors with a ground resolution of 20m. In addition there
are 3 60m bands primarily used for atmospheric correction.

Typically earth observation satellites follow a sun-synchronous orbit where orbit plane has a near constant angle to
the sun. The Senteniel 2 satellites have an orbit where each place on earth is observed at  
the same time of day and with the same photo angle every
[5th day](https://earth.esa.int/web/sentinel/user-guides/sentinel-2-msi/revisit-coverage).

Sentinel 2 data are corrected for sensor biases and geometrically corrected into a cartographic coordinate system; the
WGS84 datum and UTM set of projections.

## Different processing levels: Level-1C vs Level-2A

Level-1C is top-of-atmosphere pictures, and Level-2A are bottom-of-atmosphere pictures.
As of mid-March 2018 the processing of sentinel data are processed with L2A, but only some pictures labeled L2Ap (for prototype?) are available from before that. This means that the training data from LDir is difficult to match with well-processed satelite data.

There are two main solutions, one is to use these L2Ap-processed pictures, but we may not kow the quality of the result. There is sill merit to use this as it is easier to use if such data can be found. The quality could still be good enough, which can be expected (to some degree) as it is available to the public.

The other solution is to use certain tools to convert from L1C to L2A, such as [Sen2Cor](http://step.esa.int/main/third-party-plugins-2/sen2cor/sen2cor_v2-8/) and [Sentinel-2 Toolbox](https://sentinel.esa.int/web/sentinel/toolboxes/sentinel-2). The first one is a stanalone application, and does not contain as many features as the latter. Hence, we went with the first one, using a bash-script to call the process with relevant parameters.

### some issues with processing

Even though this works excellent, we've had some issues with processing terminating before completion, resulting in partial folder-structure and without some arbitrary number of bands. This happened both during parallel and sequential processing, but more often during parallell.

One other aspect is the time needed to process. This program might not be made to process immense amount of data. After we got more data from lDir, we downloaded Sentinel2-images for all areas provided by lDir, which resulted in between 60-70 100kmx100km tiles for each time-frame. Given that we donwloaded data for each month between May-October, beistet spent two full days on this processing alone. It's not critical, but worth mentioning.
