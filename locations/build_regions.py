import csv
import json
import logging
from pathlib import Path

import h3
import shapely

logging.basicConfig(
    format="%(asctime)-15s %(levelname)s %(module)s:%(lineno)s %(message)s",
    level=logging.DEBUG,
)

REGIONS_FILE = Path("./locations/regions.json")
OUTPUT_DIR = Path("./locations/regions/")

# The smallest resolution we're going to prepare for. (We could produce a finer
# resolution at runtime at the cost of covering more area than we'll need to,
# having discarded finer details.)
KM = 1.609344
TARGET_RADIUS = 10 * KM

res = 0
while h3.edge_length(res) > TARGET_RADIUS:
    res += 1
logging.debug("resolution %s, edge length of %s km", res, h3.edge_length(res))

logging.debug("reading countries geojson")
admin_0 = json.load(open("ne_10m_admin_0_countries_lakes.geojson"))
logging.debug("reading states/provinces geojson")
admin_1 = json.load(open("ne_10m_admin_1_states_provinces_lakes.geojson"))
logging.debug("done")


def convert_multipolygon(geometry):
    """
    h3.polyfill can read a polygon in a "GeoJSON-like" format, so we need to
    split apart MultiPolygons, and also reverse the coordinate order.
    """
    if geometry["type"] == "MultiPolygon":
        for poly in geometry["coordinates"]:
            simple_poly = {"type": "Polygon", "coordinates": []}
            for ring in poly:
                ring = [[p[1], p[0]] for p in ring]
                simple_poly["coordinates"].append(ring)
            yield simple_poly
    elif geometry["type"] == "Polygon":
        simple_poly = {"type": "Polygon", "coordinates": []}
        for ring in geometry["coordinates"]:
            ring = [[p[1], p[0]] for p in ring]
            simple_poly["coordinates"].append(ring)
        yield simple_poly
    else:
        raise ValueError(geometry["type"])


def build_country(output_path, features):
    if output_path.is_file():
        logging.debug("already exists %s", output_path)
        return
    assert not output_path.exists()
    logging.debug("reading %s features", len(features))
    hexs = set()
    for feat in features:
        for polygon in convert_multipolygon(feat["geometry"]):
            hexs.update(h3.polyfill(polygon, res))
    logging.debug("produced %s hexes", len(hexs))
    compact = h3.compact(hexs)
    logging.debug("compacted %s hexes", len(compact))
    with output_path.open("w") as f:
        writer = csv.writer(f)
        writer.writerow(["hex_id"])
        writer.writerows([hex_id] for hex_id in compact)


build_country(
    OUTPUT_DIR / "us.csv",
    [feat for feat in admin_0["features"] if feat["properties"]["SOV_A3"] == "US1"],
)
