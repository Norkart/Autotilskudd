"""Module for preparing data for cnn training and testing"""
import os
import numpy as np
import ogr, gdal, osr
import glob
import random as rn
import math as m
import re

# Stuff for decoding MGRS 100x100km tile codes
band_code_to_nr = {
    "C": -80,
    "D": -72,
    "E": -64,
    "F": -56,
    "G": -48,
    "H": -40,
    "J": -32,
    "K": -24,
    "L": -16,
    "M": -8,
    "N": 0,
    "P": 8,
    "Q": 16,
    "R": 24,
    "S": 32,
    "T": 40,
    "U": 48,
    "V": 56,
    "W": 64,
    "X": 80,
}

row_code_to_nr = [
    {
        "A": 0,
        "B": 100000,
        "C": 200000,
        "D": 300000,
        "E": 400000,
        "F": 500000,
        "G": 600000,
        "H": 700000,
        "J": 800000,
        "K": 900000,
        "L": 1000000,
        "M": 1100000,
        "N": 1200000,
        "P": 1300000,
        "Q": 1400000,
        "R": 1500000,
        "S": 1600000,
        "T": 1700000,
        "U": 1800000,
        "V": 1900000,
    },
    {
        "F": 0,
        "G": 100000,
        "H": 200000,
        "J": 300000,
        "K": 400000,
        "L": 500000,
        "M": 600000,
        "N": 700000,
        "P": 800000,
        "Q": 900000,
        "R": 1000000,
        "S": 1100000,
        "T": 1200000,
        "U": 1300000,
        "V": 1400000,
        "A": 1500000,
        "B": 1600000,
        "C": 1700000,
        "D": 1800000,
        "E": 1900000,
    }
]

col_code_to_nr = {
    "A": 100000,
    "B": 200000,
    "C": 300000,
    "D": 400000,
    "E": 500000,
    "F": 600000,
    "G": 700000,
    "H": 800000,
    "J": 100000,
    "K": 200000,
    "L": 300000,
    "M": 400000,
    "N": 500000,
    "P": 600000,
    "Q": 700000,
    "R": 800000,
    "S": 100000,
    "T": 200000,
    "U": 300000,
    "V": 400000,
    "W": 500000,
    "X": 600000,
    "Y": 700000,
    "Z": 800000,
}


class MGRS:
    """Class for handling MGSR 100x100km ctile codes"""
    def __init__(self, code):
        self.set_from_code(code)

    def set_from_code(self, code):
        """Interpret MGRS 100x100km tile code.

        The code has the shape ZZBTT where ZZ is the WGS84/UTM Zone number (1-36), B is the latitude band letter and
        TT are two letters describing the 100x100km tile"""

        re_match = re.match(r"(\d{1,2})([A-HJ-NP-Z])([A-HJ-NP-Z])([A-HJ-NP-V])", code)
        if not re_match:
            raise ValueError("Illegal MGRS code: " + code)

        self.code = code
        self.zone = int(re_match.group(1))
        self.band = re_match.group(2)
        self.col = re_match.group(3)
        self.row = re_match.group(4)

        band_lat = band_code_to_nr[self.band]
        band_y = 6400000 * m.radians(band_lat)

        n = row_code_to_nr[(self.zone - 1)%2][self.row]
        if band_y < 0:
            band_y += 10000000
        while n < band_y:
            n += 2000000

        self.e = col_code_to_nr[self.col]
        self.n = n

    def set_from_xy(self, zone, e, n, south=False):
        """unfinished and will perhaps never be used?"""
        self.zone = zone
        self.e = e
        self.n = n
        self.band = "A"

    def __repr__(self):
        return f"MGRS(code={self.code}, zone={self.zone}, band={self.band}, " \
            f"col={self.col}, row={self.row}, e={self.e}, n={self.n})"


class ImageSet:
    """Handling a Sentinel 2 tile, processing level 1C or 2A

    Parameters
    ----------
    data_path: str (directory path)
        Directory where Sentiel 2 projects are stored.
    image_set_name: str
        Project name, formatted according to theis standard:
        https://sentinel.esa.int/web/sentinel/user-guides/sentinel-2-msi/naming-convention
        Example: S2B_MSIL2A_20180715T105029_N0208_R051_T32VNN_20180715T152821
    """

    """List of channels with 10m ground resolution"""
    ch10m = ["B02", "B03", "B04", "B08"]

    """List of channels with 20m ground resolution"""
    ch20m = ["B05", "B06", "B07", "B8A", "B11", "B12"]

    def __init__(self, data_path, image_set_name):
        # Interprete project name
        re_match = re.match(r"(S2[AB])_MSIL([12][A-C])_(\d{8}T\d{6})_"
                            r"N(\d{4})_R(\d{3})_T(\d{1,2}[A-HJ-NP-Z][A-HJ-NP-Z][A-HJ-NP-V])_(\d{8}T\d{6})",
                            image_set_name)
        if not re_match:
            raise ValueError("Illegal MGRS code: " + image_set_name)

        self.image_set_name = image_set_name
        self.mission = re_match.group(1)
        self.product_level = re_match.group(2)
        self.datatake_time = re_match.group(3)
        self.processing_baseline_nr = re_match.group(4)
        self.relative_orbit_nr = re_match.group(5)
        self.tile = MGRS(re_match.group(6))
        self.product_discriminator = re_match.group(7)

        # Find and test existence of data directory in project
        image_dir = os.path.join(data_path, self.image_set_name, self.image_set_name + ".SAFE", "GRANULE")
        if not os.path.isdir(image_dir):
            raise ValueError(f"Directory does not exist: {image_dir}")

        image_dir = os.path.join(image_dir, f"L{self.product_level}_T{self.tile.code}_A*")
        glob_match = glob.glob(image_dir)
        if not glob_match:
            raise ValueError(f"Unable to find directory: {image_dir}")
        self.data_path = glob_match[0]


    def get_channel_image_filename(self, channel):
        """Extract full filename for a channel image

        Parameters
        ----------
        channel: str
            Name of the requested channel

        Returns
        -------
        str
            Full file path to image file
        """
        # GRANULE\\L2A_T32VNN_A007084_20180715T105300\\IMG_DATA\\R10m\\T32VNN_20180715T105029_B02_10m.jp2,
        if channel in ImageSet.ch10m:
            ground_resolution = 10
        elif channel in ImageSet.ch20m:
            ground_resolution = 20
        else:
            raise ValueError(f"Illegal channel: {channel}")

        # Find and test for existence of image files
        image_dir = os.path.join(self.data_path, "IMG_DATA", f"R{ground_resolution}m")
        if not os.path.isdir(image_dir):
            raise ValueError(f"Directory does not exist: {image_dir}")

        image_fn = os.path.join(image_dir, f"T{self.tile.code}_{self.datatake_time}_{channel}_{ground_resolution}m.jp2")
        if not os.path.isfile(image_fn):
            raise ValueError(f"Image file does not exist: {image_fn}")

        return image_fn

    def get_qi_path(self):
        """Return directory path ti quality information"""
        qi_path = os.path.join(self.data_path, "QI_DATA")
        if not os.path.isdir(qi_path):
            raise ValueError(f"Directory does not exist: {qi_path}")

        return qi_path

    def __repr__(self):
        return f"MGRS(mission={self.mission}, product_level={self.product_level}, datatake_time={self.datatake_time}, " \
            f"processing_baseline_nr={self.processing_baseline_nr}, relative_orbit_nr={self.relative_orbit_nr}, " \
            f"tile_id={self.tile.code}, product_discriminator={self.product_discriminator})"



def fill_features(feature_layer, feature_table, cols, rows, xform, proj, filename):
    """Fill an image with cathegorical values.

     Parameters
     ----------
     feature_layer: gdal layer
        Database or vector data file
    feature_table: [("SQL query", "Description", int), ...]
        Table of tuples of (query, description, category ix value)
    cols, rows: int
        Output image dimensions
    xform: [x0, x_scale, 0, y0, 0, y_scale]
        Affine transform relating image coordinate system and world coordinate system.
        Similar to transform used in geotiff, world files etc...
    proj: str
        WKT description of world coordinate system
    filename: str(path)
        Output filemname
     """
    # Create image
    target_ds = gdal.GetDriverByName('GTiff').Create(filename, cols, rows, 1, gdal.GDT_Byte, ['COMPRESS=LZW', 'PREDICTOR=2'])
    target_ds.SetGeoTransform(xform)
    target_ds.SetProjection(proj)

    # Set geographic search values
    x_min = xform[0]
    y_max = xform[3]
    y_min = y_max + rows * xform[5]
    x_max = x_min + cols * xform[1]

    # Create ring
    ring = ogr.Geometry(ogr.wkbLinearRing)
    ring.AddPoint(x_min, y_min)
    ring.AddPoint(x_max, y_min)
    ring.AddPoint(x_max, y_max)
    ring.AddPoint(x_min, y_max)
    ring.AddPoint(x_min, y_min)

    # Create polygon
    poly = ogr.Geometry(ogr.wkbPolygon)
    poly.AddGeometry(ring)
    srs = osr.SpatialReference()
    srs.ImportFromWkt(proj)
    poly.AssignSpatialReference(srs)
    poly.TransformTo(feature_layer.GetSpatialRef())

    # set spatial filter
    feature_layer.SetSpatialFilter(poly)

    # Fill raster
    for feature in feature_table:
        # Rasterize
        # Set search string
        feature_layer.SetAttributeFilter(feature[0])
        if feature_layer.GetFeatureCount() > 0:
            if gdal.RasterizeLayer(target_ds, [1], feature_layer, burn_values=[feature[2]], options=['ALL_TOUCHED=TRUE']) != 0:
                raise Exception(f"error rasterizing layer: {feature[1]}")

    return target_ds


def image_set_load(image_path_list):
    """Load a set of images of identical dimension and coordinate system

    Parmeters
    ---------
    image_path_list: list(str)
        List of image file names

    Returns
    -------
    np_bands: list(ndarray(rows, cols))
    cols, rows: int
    xform: [x0, x_scale, 0, y0, 0, y_scale]
        Affine transform relating image coordinate system and world coordinate system.
        Similar to transform used in geotiff, world files etc...
    projstr
        WKT description of world coordinate system
    """
    np_bands = []

    xform = None
    proj = None
    rows = None
    cols = None
    for image_path in image_path_list:
        img = gdal.Open(image_path)
        if not img:
            print(f"Bilde {image_path} ikke lastet")
            continue

        if not xform:
            xform = img.GetGeoTransform()
        elif img.GetGeoTransform() != xform:
            print(f"Bilde {image_path} har annet koordinatsystem ({img.GetGeoTransform()}) enn de andre ({xform})")
            continue
        if not proj:
            proj = img.GetProjection()
        elif img.GetProjection() != proj:
            print(f"Bilde {image_path} har annen projeksjon ({img.GetProjection()}) enn de andre ({proj})")
            continue
        if not cols:
            cols = img.RasterXSize
        elif cols != img.RasterXSize:
            print(f"Bilde {image_path} har annen størrelse ({img.RasterXSize}) enn de andre ({cols})")
            continue
        if not rows:
            rows = img.RasterYSize
        elif rows != img.RasterYSize:
            print(f"Bilde {image_path} har annen størrelse ({img.RasterYSize}) enn de andre ({rows})")
            continue

        band = img.GetRasterBand(1)
        np_band = band.ReadAsArray()
        np_bands.append(np_band)
    return np_bands, cols, rows, xform, proj


def generate_training_data_from_image(image_set, feature_layer, feature_table, patch_sz, out_path):
    """Save data from large satelite image into smaller files more well suited for machine learning

    Parameters
    ----------
    image_set: ImageSet
        The satelite 100x100km tile
    feature_layer, feature_table:
        See :func:'training_data.fill_features()'
    patch_sz: int
        Size of patches (pixels at base resolution)
    out_path: str
        Path to root of training data
    """
    # Prepare output directory
    out_path = os.path.join(out_path, f"{image_set.tile.zone:02}{'S' if band_code_to_nr[image_set.tile.band] < 0 else 'N'}")
    out_path = os.path.join(out_path, f"{image_set.tile.n // 100000:02}_{image_set.tile.e // 100000:01}")
    os.makedirs(out_path, exist_ok=True)

    # Make list of lienames
    image_path_list_10m = [image_set.get_channel_image_filename(ch) for ch in ImageSet.ch10m]
    image_path_list_20m = [image_set.get_channel_image_filename(ch) for ch in ImageSet.ch20m]

    # Load data
    np_bands_10m, cols_10m, rows_10m, xform_10m, proj_10m = image_set_load(image_path_list_10m)
    np_bands_20m, cols_20m, rows_20m, xform_20m, proj_20m = image_set_load(image_path_list_20m)

    # Load [Cloudcover, Snowcover] images
    bands_cld_snw, cols_cld_snw, rows_cld_snw, xform_cld_snw, proj_cld_snw = \
        image_set_load([os.path.join(image_set.get_qi_path(), "MSK_CLDPRB_20m.jp2"),
                        os.path.join(image_set.get_qi_path(), "MSK_SNWPRB_20m.jp2")])

    cld_array = bands_cld_snw[0]
    snw_array = bands_cld_snw[1]

    # Image patch position
    ground_res = 10
    n = int(m.floor((image_set.tile.n + 100000) / (patch_sz * ground_res))) * patch_sz * ground_res
    while n > image_set.tile.n:
        e = int(m.ceil(image_set.tile.e / (patch_sz * ground_res))) * patch_sz * ground_res
        while e < image_set.tile.e + 100000:
            i = int((e - xform_10m[0]) //  xform_10m[1])
            j = int((n - xform_10m[3]) //  xform_10m[5])

            # Check cloud and snowcover
            cld_cover = 0
            snw_cover = 0
            for ci in range(i // 2, (i +  patch_sz) // 2):
                for cj in range(j // 2, (j + patch_sz) // 2):
                    cld_cover = min(cld_array[cj, ci] / 50, 1.0)
                    snw_cover = min(snw_array[cj, ci] / 50, 1.0)

            if cld_cover >= (patch_sz/2)**2 * 0.1 or snw_cover >= (patch_sz/2)**2 * 0.1:
                continue



            # Create output directory
            img_out_path = os.path.join(out_path, f"{n // 10000 % 10}_{e // 10000 % 10}")
            os.makedirs(img_out_path, exist_ok=True)

            # Compute image transform
            img_xform_10m = (e, xform_10m[1], xform_10m[2],
                             n, xform_10m[4], xform_10m[5])
            img_xform_20m = (e, xform_20m[1], xform_20m[2],
                             n, xform_20m[4], xform_20m[5])

            # Create colorimage for ML source
            # 10m images
            fn = os.path.join(img_out_path, f"{n}_{e}_{patch_sz}_10_{image_set.image_set_name}_B02B03B04B08.tif")
            ds = gdal.GetDriverByName('GTiff').Create(fn,
                                                      patch_sz, patch_sz, len(np_bands_10m), gdal.GDT_UInt16,
                                                      ['COMPRESS=LZW', 'PREDICTOR=2'])
            ds.SetGeoTransform(img_xform_10m)
            ds.SetProjection(proj_10m)

            # Fill with data
            for band_nr, array in enumerate(np_bands_10m):
                patch = array[j:j + patch_sz, i:i +  patch_sz]
                ds.GetRasterBand(band_nr + 1).WriteArray(patch)

            # 20m images
            fn = os.path.join(img_out_path, f"{n}_{e}_{patch_sz//2}_20_{image_set.image_set_name}_B05B06B07B8AB11B12.tif")
            ds = gdal.GetDriverByName('GTiff').Create(fn,
                                                      patch_sz // 2, patch_sz // 2, len(np_bands_20m), gdal.GDT_UInt16,
                                                      ['COMPRESS=LZW', 'PREDICTOR=2'])
            ds.SetGeoTransform(img_xform_20m)
            ds.SetProjection(proj_20m)

            # Fill with data
            for band_nr, array in enumerate(np_bands_20m):
                patch = array[j // 2: (j + patch_sz) // 2, i // 2: (i + patch_sz) // 2]
                ds.GetRasterBand(band_nr + 1).WriteArray(patch)
            ds = None

            # Create categorical image of feature layers
            fn = os.path.join(img_out_path, f"{n}_{e}_{patch_sz}_10_AR5.tif")
            if not os.path.exists(fn):
                # Create only if it doesn't exist
                fill_features(feature_layer, feature_table, patch_sz, patch_sz, img_xform_10m, proj_10m, fn)

            e += patch_sz * ground_res
        n -= patch_sz * ground_res


data_path = "data"

def generate_training_data_ar5(image_sets):
    patch_sz = 128

    # Postgres stuff
    pg_server = "pgdvhro.webdmz.no"
    pg_port = "5432"
    pg_dbname = "datavarehus"
    pg_user = "datavarehus_ro"
    pg_passw = "7mr6ue"
    pg_layer = "fkb.v_kommunene_104_arealressursflate"
    connString = f"PG: host={pg_server} port={pg_port} dbname={pg_dbname} user={pg_user} password={pg_passw}"
    conn = ogr.Open(connString)
    feature_layer = conn.GetLayer(pg_layer)

    feature_table = [
        ("artype >= 90", "Unknown/novalue", 0),
        ("artype =  30 and artreslag =  31", "Barskog", 1),
        ("artype =  30 and artreslag =  32", "Loevskog", 2),
        ("artype =  30 and artreslag >= 33", "Skog, blandet eller ukjent", 3),
        ("artype =  50 and argrunnf >= 43 and argrunnf <= 45", "Jorddekt åpen mark", 4),
        ("artype >= 20 and artype < 30", "Dyrket", 5),
        ("artype =  50 and argrunnf = 41", "Blokkmark", 6),
        ("artype =  50 and argrunnf = 42", "Fjell i dagen", 7),
        ("artype =  60", "Myr", 8),
        ("artype =  70", "Sne/is/bre", 9),
        ("artype =  50 and argrunnf > 45", "Menneskepaavirket eller ukjent åpen mark", 11),
        ("artype >= 80 and artype < 89", "Water", 10),
        ("artype =  12", "Vei/jernbane/transport", 12),
        ("artype >= 10 and artype < 12", "Bebygd", 13),
    ]

    for image_set in image_sets:
        generate_training_data_from_image(ImageSet(data_path, image_set),
                                          feature_layer, feature_table,
                                          patch_sz, os.path.join(data_path, "training"))

def generate_training_data_ldir(image_sets):
    patch_sz = 128

    # Postgres stuff
    pg_server = "beistet"
    pg_port = "5433"
    pg_dbname = "LDir"
    pg_user = "postgres"
    pg_passw = "1234"
    pg_layer = "pa"
    connString = f"PG: host={pg_server} port={pg_port} dbname={pg_dbname} user={pg_user} password={pg_passw}"
    conn = ogr.Open(connString)
    feature_layer = conn.GetLayer(pg_layer)

    feature_table = [
        ("prod = 'Gras'", "Gress", 1),
        ("prod = 'Korn'", "Korn", 2),
    ]

    for image_set in image_sets:
        generate_training_data_from_image(ImageSet(data_path, image_set),
                                          feature_layer, feature_table,
                                          patch_sz, os.path.join(data_path, "training"))


def generate_training_data(image_sets):
    generate_training_data_ar5(image_sets)

def mix_training_data():
    train_sz = 4000
    valid_sz = 200
    test_sz = 200
    target_data_set = glob.glob(os.path.join(data_path, "training", "*", "*", "*", "*_AR5.tif"))

    data_set = []
    for fn in target_data_set:

        img = gdal.Open(fn)
        if not img:
            continue
        arr = img.GetRasterBand(1).ReadAsArray()
        sum_type = np.zeros(14)
        for i in range(arr.shape[0]):
            for j in range(arr.shape[1]):
                sum_type[arr[i,j]] += 1
        sum_type /= arr.shape[0] * arr.shape[1]

        # Mye dyrka og annen åpen mark
        if sum_type[5] + sum_type[4] < 0.15:
            continue
        # Noe vei, bygg eller vann
        if sum_type[10] + sum_type[11] + sum_type[12] + sum_type[13] < 0.05:
            continue
        # Men ikke for mye vann
        if sum_type[10] > 0.4:
            continue
        # og ikke for mye skog
        if sum_type[1] + sum_type[2] + sum_type[3] > 0.6:
            continue

        # Use images
        src_10m_list = glob.glob(fn[:-7] + "*_B02B03B04B08.tif")
        for src_10m in src_10m_list:
            src_20m = src_10m[:-16] + "B05B06B07B8AB11B12.tif"
            src_20m = src_20m.replace("_128_10_", "_64_20_")
            if os.path.isfile(src_20m):
                data_set.append((src_10m, src_20m, fn))

    # If we have less than the requested number of training files, adjust numbers of training, validation and test images
    if train_sz + valid_sz + test_sz > len(data_set):
        valid_frac = valid_sz / (train_sz + valid_sz + test_sz)
        test_frac = test_sz / (train_sz + valid_sz + test_sz)
        valid_sz = int(m.ceil(valid_frac * len(data_set)))
        test_sz = int(m.ceil(test_frac * len(data_set)))
        train_sz = len(data_set) - valid_sz - test_sz

    # Random shuffle
    rn.shuffle(data_set)

    # Split into training, validation and test set
    with open(os.path.join(data_path, "train_set.txt"), "w") as file:
        for fn in data_set[:train_sz]:
            print(fn, file=file)

    with open(os.path.join(data_path, "valid_set.txt"), "w") as file:
        for fn in data_set[train_sz:train_sz+valid_sz]:
            print(fn, file=file)

    with open(os.path.join(data_path, "test_set.txt"), "w") as file:
        for fn in data_set[train_sz+valid_sz:train_sz+valid_sz+test_sz]:
            print(fn, file=file)

def main():
    image_sets = [
        "S2B_MSIL2A_20180715T105029_N0208_R051_T32VNN_20180715T152821",
        "S2B_MSIL2A_20180715T105029_N0208_R051_T32VMM_20180715T152821",
        "S2B_MSIL2A_20180821T104019_N0208_R008_T32VNM_20180821T170337",
        "S2B_MSIL2A_20181010T104019_N0209_R008_T32VNM_20181010T171128",
        # "S2B_MSIL2A_20190319T104019_N0211_R008_T32VNM_20190319T151229",
    ]
    # generate_training_data(image_sets)
    mix_training_data()

    #print(ImageSet("S2B_MSIL2A_20180715T105029_N0208_R051_T32VNN_20180715T152821"))
    #print(ImageSet("S2B_MSIL2A_20180715T105029_N0208_R051_T32VMM_20180715T152821"))
    #print(ImageSet("S2B_MSIL2A_20180821T104019_N0208_R008_T32VNM_20180821T170337"))
    #print(ImageSet("S2B_MSIL2A_20181010T104019_N0209_R008_T32VNM_20181010T171128"))

    #print(MGRS("32VMM"))
    #print(MGRS("12SVL"))
    #print(MGRS("12RVL"))
    #print(MGRS("15TVE"))
    #print(MGRS("15SVE"))
    #print(MGRS("15SWC"))

if __name__ == "__main__":
    main()
