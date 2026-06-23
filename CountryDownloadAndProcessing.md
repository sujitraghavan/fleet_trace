Invoke-WebRequest -Uri "http://download.geofabrik.de/south-america/paraguay-latest.osm.pbf" -OutFile ./data/paraguay-latest.osm.pbf

# 1️⃣ Extract
docker run --rm -v "${PWD}\data\graph-cache\:/data" osrm/osrm-backend `
    osrm-extract -p /opt/car.lua /data/paraguay-latest.osm.pbf

# 2️⃣ Partition
docker run --rm -v "${PWD}\data\graph-cache\:/data" osrm/osrm-backend `
    osrm-partition /data/paraguay-latest.osm.pbf

# 3️⃣ Customize
docker run --rm -v "${PWD}\data\graph-cache\:/data" osrm/osrm-backend `
    osrm-customize /data/paraguay-latest.osm.pbf


docker run -t -i -p 5000:5000 -v "${PWD}\data:/data" ghcr.io/project-osrm/osrm-backend osrm-routed --algorithm mld /data/paraguay-latest.osrm