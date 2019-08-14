"""Module for searching and loading of Sentinel 2 satelite images, very incomplete and not very usable"""
#First import all needed modules
import sentinelsat
import pandas as pd
import datetime as dt
from collections import defaultdict
import ogr
import re
import psycopg2

def envelope_polygon(geom):
    (minX, maxX, minY, maxY) = geom.GetEnvelope()

    # Create ring
    ring = ogr.Geometry(ogr.wkbLinearRing)
    ring.AddPoint(minX, minY)
    ring.AddPoint(maxX, minY)
    ring.AddPoint(maxX, maxY)
    ring.AddPoint(minX, maxY)
    ring.AddPoint(minX, minY)

    # Create polygon
    poly_envelope = ogr.Geometry(ogr.wkbPolygon)
    poly_envelope.AddGeometry(ring)
    return poly_envelope

# Login info to the sentinel2 repository
api = sentinelsat.SentinelAPI('runaas', 'FineBilder', 'https://scihub.copernicus.eu/dhus')

# Login to the database
with psycopg2.connect("host=beistet port=5433 dbname=LDir user=postgres password=1234") as conn:
    with conn.cursor("geo_cur") as cur:
        # Do reqest
        # This should be narrowed down, currently it retrieves the whole database...
        cur.execute("""SELECT ST_AsBinary(geog), dp_fra, dp_til FROM pa""")
        dp_fra = dt.date.today()
        dp_til = dt.date.min
        geo_collection = ogr.Geometry(ogr.wkbMultiPolygon)
        for row in cur:
            geo_frm_db = ogr.CreateGeometryFromWkb(row[0])
            if row[1] and row[1] < dp_fra:
                dp_fra = row[1]
            if row[2] and row[2] > dp_til:
                dp_til = row[2]
            for geo in geo_frm_db:
                # Use envelope polygon to reduce data volume
                geo_collection.AddGeometry(envelope_polygon(geo))

# Merge all intersecting polygons
union_collection = geo_collection.UnionCascaded()

# specify start and end date
dateStart = f"{dp_fra.year:04}{dp_fra.month:02}{dp_fra.day:02}"
dateEnd = f"{dp_til.year:04}{dp_til.month:02}{dp_til.day:02}"


poly_wkt = union_collection.ExportToWkt()

# Do request
products = api.query(poly_wkt,
                     date=(dateStart, dateEnd),
                     platformname='Sentinel-2',
                     cloudcoverpercentage=(0, 30))

# Convert to geopandas
prod_gdf = api.to_geodataframe(products)


tiles = defaultdict(lambda : defaultdict(list))
for row in prod_gdf.itertuples(name="SentenielProject"):
    re_match = re.match(r"S(2[AB])_MSIL([12][AC])_(\d{8}T\d{6})_N\d{4}_R\d{3}_T(\d{2}[A-Z]{3})", row.title)
    mission = re_match.group(1)
    product = re_match.group(2)
    date = re_match.group(3)
    tile = re_match.group(4)
    tiles[tile][date].append(row)

for tile, dates in tiles.items():
    print(tile)
    for date, values in dates.items():
        print("   ", date)
        for p in values:
            print("       ", p)

prod_gj = api.to_geojson(products)

with open("satelitter.json", "w") as f:
    print(prod_gj, file=f)

# Export to csv
# prod_gdf.to_csv("satelitter.csv", sep=";")