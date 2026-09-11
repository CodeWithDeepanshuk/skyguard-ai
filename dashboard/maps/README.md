# Station map assets

Leaflet 1.9.4 is vendored under ../vendor/leaflet, including its license.
World land polygons: Natural Earth ne_110m_land (public-domain map data), from
https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/ne_110m_land.geojson

The local land layer supplies coarse coastlines offline; it is not a street map
and does not represent administrative boundaries. Online street tiles are served
by https://tile.openstreetmap.org with visible contributor attribution. Tiles are
not bulk-downloaded or pre-cached. If tiles fail, the local coastline is retained.
Station coordinates and selection come from the existing station API; this map
does not modify anomaly scores or health calculations.
