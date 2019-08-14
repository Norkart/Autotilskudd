# API (server.py)

The server is started by issuing the command `$ python server.py`. This has only been tested on Ubuntu 18.04.

NOTE: If the server is to be migrated to somewhere else, remember to allow connections to the port that the server listens on (and of course, remember to update the endpoint; the probability that the new server has the same IP is rather small).
The client can send a POST request to the endpoint `192.168.3.196:XX/Prediction` where `XX` denotes which port the server is listening on. Currently, that port is configured to `XX = 5000`.

# Methods

POST
The body of the POST request must contain a query polygon formatted according to the "geometry" field of the GeoJSON format.
Example of valid query polygon: `{"type": "Polygon", "coordinates": [ [ [10.9688182598784,59.246360626789], [10.9688465457549,59.2463225059688], [10.9688465927749,59.2463224803992], [10.9688182598784,59.246360626789] ] ] }`

The coordinates of the query polygon must be in the EPSG 4326 format (although the coordinates have to be reversed as opposed to the standard; instead of the order `[latitude, longitude]`, the server expects the coordinates to be in the reverse order, i.e. `[longitude, latitude]`.)
The response to the request is GeoJSON describing all the polygons that are predicted to contain either grain or grass. Below is an example response:

`{ "type": "FeatureCollection", "name": "Polygons", "features": [ { "type": "Feature", "properties": { "category": 2 }, "geometry": { "type": "Polygon", "coordinates": [ [ [ 10.970881883823715, 59.24782869396987 ], [ 10.970858440130597, 59.24783455811488 ], [ 10.9708584281719, 59.247834560099484 ], [ 10.970822541266719, 59.24783776111994 ], [ 10.970881883823715, 59.24782869396987 ] ] ] } }, { "type": "Feature", "properties": { "category": 2 }, "geometry": { "type": "Polygon", "coordinates": [ [ [ 10.967642598218895, 59.2456218209094 ], [ 10.967788941865157, 59.24562708522448 ], [ 10.96768774841952, 59.24562830975327 ], [ 10.967642598218895, 59.2456218209094 ] ] ] } } ] }`

Each feature in the GeoJSON also contains a field called "category" inside the field "properties". The value in the category field denotes whether the polygon corresponds to grain or grass; 1 corresponds to grass and 2 corresponds to grain.

# How the API works conceptually

Figuring out how to design the internal pipeline of the API was not trivial. This is an attempt to elicit the inner workings of that very pipeline, as well as justifications for certain design choices.

The API receives a query polygon from the client in the format specified above. The choice of that particular EPSG reference is standardized -- but the order of the coordinates is not, and hence may seem arbitrary. The reason the coordinates are in this particular order is because of the client's internal design.

The raster images used for prediction by the server have filenames that convey their structure. The filenames consist of tokens, and the tokens are separated by underscores (the character "\_"). An example of such a filename is `6680320_581120_64_20_S2A_MSIL2A_20180727T104021_N0208_R008_T32VNM_20180727T134459_B05B06B07B8AB11B12.tif`. The tokens important for the server are the first four. The first two tokens are the north and east coordinates of the upper left corner of the raster image, respectively. The third token is the width (and hence the height) of the image, and the fourth token is the pixel resolution (in meters) of the image. These tokens are used in conjunction to calculate a bounding box for each raster image.

The server uses its internal representation of the query polygon and transforms its coordinates so that they match the coordinate system of the raster images (EPSG 25832), and a bounding box is calculated (because a bounding box is easier to work with, and the end result is not impacted by the utilization of a bounding box instead of the query polygon). The bounding box is then used to find the raster images that intersect it.

The raster images that intersect the bounding box of the query polygon are then used for prediction, and combined into a single raster image. To see how this composition of smaller images into a single large one is done in detail, you may want to consult the source code located in `server.py`.

The single raster image is then polygonized to obtain regions that may contain grain or grass. These polygons are then intersected with the query polygon so that the client receives only polygons that are contained within the query polygon.

# Improving the boundaries using AR5 data

In the latest iteration of the prototype server, AR5 polygons are used to obtain smooth polygon boundaries; the ANN merely serves as support -- it helps determine whether the polygons obtained from AR5 are grain or grass.
