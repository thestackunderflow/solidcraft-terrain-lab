"""Download the heights: USGS 3DEP elevation, ImageServer exportImage (public domain, no account needed).

    python3 terrain/get_data.py            (in the lab image: needs network)

Change ONE line for your own place: BBOX (west, south, east, north in degrees). Writes data/picture-grid.tif (400 x 320
samples, square pixels: the server forces square pixels, so a grid whose shape differs from the box's shape comes back
covering a bigger box; make_slices.py samples the slices from this grid) and data/SOURCE.json (URL, date, sha256). Credit: "Map services and data available from U.S. Geological Survey, National
Geospatial Program."
"""
import datetime
import hashlib
import json
import os
import urllib.parse
import urllib.request

BBOX = (-122.24, 46.16, -122.14, 46.24)          # Mount St. Helens: change this line for your place
URL = 'https://elevation.nationalmap.gov/arcgis/rest/services/3DEPElevation/ImageServer/exportImage'
HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, '..', 'data')


def fetch(cols, rows, name):
    q = {'bbox': ','.join(str(v) for v in BBOX), 'bboxSR': 4326, 'imageSR': 4326, 'size': f'{cols},{rows}',
         'format': 'tiff', 'pixelType': 'F32', 'interpolation': 'RSP_BilinearInterpolation', 'f': 'image'}
    url = URL + '?' + urllib.parse.urlencode(q)
    req = urllib.request.Request(url, headers={'User-Agent': 'StackUnderflow-solidcraft-terrain-lab/1.0'})
    body = urllib.request.urlopen(req, timeout=120).read()
    with open(os.path.join(DATA, name), 'wb') as f:
        f.write(body)
    return {'file': 'data/' + name, 'url': url, 'bytes': len(body), 'sha256': hashlib.sha256(body).hexdigest()}


if __name__ == '__main__':
    os.makedirs(DATA, exist_ok=True)
    src = {'source': 'USGS 3DEP, ImageServer exportImage', 'bbox_wsen_deg': list(BBOX),
           'fetched_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='seconds'),
           'credit': 'Map services and data available from U.S. Geological Survey, National Geospatial Program.',
           'files': [fetch(400, 320, 'picture-grid.tif')]}
    import sys
    sys.path.insert(0, os.path.join(HERE, '..'))
    from terrain.sections import pixel_scale
    sx, sy = pixel_scale(os.path.join(DATA, 'picture-grid.tif'))[:2]   # the grid must cover exactly BBOX
    assert abs(sx * 400 - (BBOX[2] - BBOX[0])) < 1e-6 and abs(sy * 320 - (BBOX[3] - BBOX[1])) < 1e-6, (sx, sy)
    with open(os.path.join(DATA, 'SOURCE.json'), 'w', encoding='utf-8', newline='\n') as f:
        json.dump(src, f, indent=1)
    print(json.dumps(src, indent=1))
