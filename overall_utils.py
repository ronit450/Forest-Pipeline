import json
import rasterio
import numpy as np
import re
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
import matplotlib.patheffects as path_effects
from shapely.geometry import LineString, Point
import math
from shapely.geometry import Polygon, LineString, mapping
from collections import defaultdict
from rasterio.plot import show
from geopy.distance import geodesic
from pyproj import Transformer
from matplotlib.patches import Circle
import re,os
import boto3
from urllib.parse import urlparse
from boto3.s3.transfer import TransferConfig
import shutil
from botocore.exceptions import ClientError
import logging
logger = logging.getLogger(__name__)

class TreeUtils:
    def __init__(self):
        self.health_Colours = {'0': '#E3412B', '1': '#FBAA35', '2': '#30C876', '3': '#1E8C4D'}
        self.transformer = Transformer.from_crs("EPSG:4326", "EPSG:3857", always_xy=True)

    def total_coniffer(self, json_file):
        with open(json_file, 'r') as file:
            data = json.load(file)
        return sum(1 for shape in data['shapes'] if shape.get('label') == '0')

    def image_area(self, image):
        with rasterio.open(image) as src:
            # Get bounds in WGS84
            bounds = src.bounds
            # Calculate area using geodesic measurements
            corners = [
                (bounds.bottom, bounds.left),
                (bounds.bottom, bounds.right),
                (bounds.top, bounds.right),
                (bounds.top, bounds.left)
            ]
            polygon = Polygon(corners)
            return self.calculate_geographic_area(polygon)

    def calculate_geographic_area(self, polygon):
        """Calculate area of a polygon in square meters using geodesic measurements"""
        geom = gpd.GeoSeries([polygon], crs="EPSG:4326")
        geom_proj = geom.to_crs("EPSG:3857")
        return geom_proj.area.iloc[0]

    def scoout_area(self):
        return f"15* 15"

    def extract_plot_and_stratum(self, path):
        match = re.search(r"_(\d+)([A-Z])_", path)
        if match:
            plot_number = match.group(1)
            stratum = match.group(2)
            return plot_number, stratum

    def data_csv(self, csv_path, plot_number, stratum):
        data = pd.read_csv(csv_path)
        filtered_data = data[(data['plot'] == int(plot_number)) & (data['stratum'] == stratum)]
        result = filtered_data[['location', 'block', 'slashArea', 'voidArea', 'flightDate', 'treeType']].iloc[0].to_dict()
        return result

    def get_line_color(self, distance):
        if distance < 1:
            return 'red'
        if distance <= 2:
            return 'yellow'
        return 'green'

    def calculate_distance(self, point1, point2):
        """Calculate distance between two points in meters using geodesic distance"""
        return geodesic(
            (point1.y, point1.x),  # Convert to (lat, lon) for geodesic
            (point2.y, point2.x)
        ).meters


    def create_segment_connections(self, input_geojson_path, output_geojson_path):
        with open(input_geojson_path, 'r') as f:
            data = json.load(f)
        
        segments = []
        for i, feature in enumerate(data['features']):
            polygon_coords = feature['geometry']['coordinates'][0]
            polygon = Polygon(polygon_coords)
            centroid = polygon.centroid
            segments.append({
                'id': i,
                'centroid': Point(centroid.x, centroid.y)
            })
        
        lines_features = []
        processed_pairs = set()
        
        for i, seg1 in enumerate(segments):
            for j, seg2 in enumerate(segments):
                if i >= j:
                    continue
                    
                pair_id = tuple(sorted([i, j]))
                if pair_id in processed_pairs:
                    continue
                
                processed_pairs.add(pair_id)
                
                # Calculate geodesic distance in meters
                distance = self.calculate_distance(seg1['centroid'], seg2['centroid'])
                
                if distance <= 3:  
                    line = LineString([
                        (seg1['centroid'].x, seg1['centroid'].y),
                        (seg2['centroid'].x, seg2['centroid'].y)
                    ])
                    
                    if distance < 1:
                        line_class = '2'
                    elif distance <= 2:
                        line_class = '1'
                    else:
                        line_class = '0'
                    
                    feature = {
                        "type": "Feature",
                        "geometry": mapping(line),
                        "properties": {
                            "class": line_class,
                            "distance": round(distance, 3),
                        }
                    }
                    lines_features.append(feature)
        
        output_geojson = {
            "type": "FeatureCollection",
            "crs": {
                "type": "name",
                "properties": {
                    "name": "urn:ogc:def:crs:EPSG::4326"
                }
            },
            "features": lines_features
        }
        
        with open(output_geojson_path, 'w') as f:
            json.dump(output_geojson, f, indent=2)
    
    def upload_to_s3(lself, local_file_path, bucket_name, folder_key):
        s3 = boto3.client('s3')
        
        s3_key = folder_key
        
        config = TransferConfig(
            multipart_threshold=25 * 1024 * 1024,
            max_concurrency=10,
            multipart_chunksize=25 * 1024 * 1024,
            use_threads=True
        )
        
        try:
            logger.info(f"Uploading {local_file_path} to s3://{bucket_name}/{s3_key}")
            s3.upload_file(
                local_file_path, 
                bucket_name, 
                s3_key, 
                Config=config
            )
            s3_url = f"s3://{bucket_name}/{s3_key}"
            logger.info(f"Upload completed: {s3_url}")
            return s3_url
            
        except Exception as e:
            logger.error(f"Error uploading file {local_file_path} to S3: {e}")
            return None
    
    
            
            
class TreeVectorViz:
    def __init__(self):
        self.health_colors = {'0': '#E3412B', '1': '#FBAA35', '2': '#30C876', '3': '#1E8C4D'}
        self.line_colors = {'0': '#3EBCA1', '1': '#D9D9D9', '2': '#FD3E3E'}

    def get_point_color(self, height):
        if height <= 1.5:
            return 'orange'
        if height <= 2.5:
            return 'yellow'
        return 'lime'

    def transform_to_image_crs(self, gdf, image_crs):
        if gdf.crs is None:
            gdf.set_crs(epsg=4326, inplace=True)
        return gdf.to_crs(image_crs)

    def plot_vector_visualization(self, image_path, lines_geojson_path, wellspace_geojson_path, 
                                segments_geojson_path, output_path):
        lines_gdf = gpd.read_file(lines_geojson_path)
        wellspace_gdf = gpd.read_file(wellspace_geojson_path)
        segments_gdf = gpd.read_file(segments_geojson_path)

        with rasterio.open(image_path) as src:
            image_crs = src.crs
            if image_crs is None:
                raise ValueError("Image CRS not found. Please ensure the image has a valid CRS.")
            image = src.read()
            bounds = src.bounds
            transform = src.transform
            meta = src.meta.copy()

        plt.rcParams['figure.dpi'] = 200
        fig, ax = plt.subplots(figsize=(8, 8))

        extent = [bounds.left, bounds.right, bounds.bottom, bounds.top]
        show(image, ax=ax, extent=extent)
        ax.set_xlim([bounds.left, bounds.right])
        ax.set_ylim([bounds.bottom, bounds.top])

        lines_gdf_transformed = self.transform_to_image_crs(lines_gdf, image_crs)
        wellspace_gdf_transformed = self.transform_to_image_crs(wellspace_gdf, image_crs)
        segments_gdf_transformed = self.transform_to_image_crs(segments_gdf, image_crs)

        for _, segment in segments_gdf_transformed.iterrows():
            class_value = segment['class']
            color = self.health_colors[class_value]
            
            if segment.geometry.geom_type == 'Polygon':
                coords = np.array(segment.geometry.exterior.coords)
                poly = plt.Polygon(coords, 
                                 facecolor=color,
                                 alpha=0.3,
                                 edgecolor=color,
                                 linewidth=1,
                                 zorder=1)
                ax.add_patch(poly)

        for _, line in lines_gdf_transformed.iterrows():
            line_class = line['class']
            distance = line['distance']
            coords = line.geometry.coords
            
            x_coords, y_coords = zip(*coords)
            
            ax.plot(x_coords, y_coords, 
                   color='white',
                   linestyle='-',
                   linewidth=3,
                   alpha=0.7,
                   zorder=2)
            
            ax.plot(x_coords, y_coords, 
                   color=self.line_colors[line_class],
                   linestyle='-',
                   linewidth=2,
                   alpha=0.7,
                   zorder=3)
            
            dx = coords[1][0] - coords[0][0]
            dy = coords[1][1] - coords[0][1]
            mid_x = (coords[0][0] + coords[1][0]) / 2
            mid_y = (coords[0][1] + coords[1][1]) / 2
            
            angle = np.degrees(np.arctan2(dy, dx))
            
            line_length = np.sqrt(dx**2 + dy**2)
            offset = 0.1
            offset_x = -dy / line_length * offset
            offset_y = dx / line_length * offset

            ax.text(mid_x + offset_x, mid_y + offset_y, 
                   f'{distance:.2f}m',
                   color='white',
                   fontweight='bold', 
                   fontsize=4,
                   ha='center',
                   va='center',
                   rotation=angle)

        for _, point in wellspace_gdf_transformed.iterrows():
            x, y = point.geometry.x, point.geometry.y
            height = point['height_meters']
            well_spaced = point['class']
            
            ax.add_patch(Circle(
                (x, y),
                0.2,
                color='white',
                zorder=5
            ))
            
            ax.add_patch(Circle(
                (x, y),
                0.15,
                color=self.get_point_color(height),
                zorder=6
            ))
            
            if well_spaced == '1':
                ax.add_patch(Circle(
                    (x, y),
                    0.07,
                    color='black',
                    zorder=7,
                    alpha=0.5
                ))
            
            ax.text(x, y + 0.3,
                   f'{height:.2f}m',
                   color='white',
                   fontsize=6,
                   fontweight='bold',
                   ha='center',
                   va='bottom',
                   bbox=dict(
                       facecolor='black',
                       edgecolor='none',
                       alpha=0.7,
                       pad=0.3,
                       boxstyle='round'
                   ),
                   zorder=8)

        ax.set_axis_off()
        plt.tight_layout(pad=0)
        
        fig.canvas.draw()
        width, height = fig.canvas.get_width_height()
        plot_data = np.frombuffer(fig.canvas.buffer_rgba(), dtype=np.uint8)
        plot_data = plot_data.reshape((height, width, 4))[:,:,:3]
        
        meta.update({
            'count': 3,
            'dtype': 'uint8',
            'width': width,
            'height': height,
        })
        
        with rasterio.open(output_path, 'w', **meta) as dst:
            for i in range(3):
                dst.write(plot_data[:, :, i], i + 1)
                
        plt.close()
