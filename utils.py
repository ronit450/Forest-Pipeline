import rasterio
import json
import numpy as np
import cv2
from shapely.geometry import Polygon, mapping
import geopandas as gpd
import math
from rasterio.enums import Resampling

class UtilsHealth:
    def __init__(self, reference_areas):
        self.reference_areas = reference_areas
        self.target_gsd = 0.02

    def json_loader(self, json_path):
        with open(json_path, 'r') as f:
            data = json.load(f)
        results = []
        for shape in data.get("shapes", []):
            label = shape.get("label", "")
            points = shape.get("points", [])
            results.append({"label": label, "points": points})
        return results

    def resample_raster(self, src, scale_factor):
        data = src.read(
            out_shape=(
                src.count,
                int(src.height * scale_factor),
                int(src.width * scale_factor)
            ),
            resampling=Resampling.bilinear
        )
        transform = rasterio.Affine(
            src.transform.a / scale_factor,
            src.transform.b,
            src.transform.c,
            src.transform.d,
            src.transform.e / scale_factor,
            src.transform.f
        )
        return data, transform

    def convert_gsd_to_meters(self, gsd_degrees, latitude):
        lat_length_meters = 111320
        lon_length_meters = 111320 * math.cos(math.radians(latitude))
        gsd_meters = (
            abs(gsd_degrees[0]) * lon_length_meters,
            abs(gsd_degrees[1]) * lat_length_meters
        )
        return gsd_meters

    def vari_calculator(self, rgb_data):
        red_band = rgb_data[0].astype(float)
        green_band = rgb_data[1].astype(float)
        blue_band = rgb_data[2].astype(float)
        
        vari = (green_band - red_band) / (green_band + red_band - blue_band + 1e-10)
        vari_min = vari.min()
        vari_max = vari.max()
        normalized_vari = (vari - vari_min) / (vari_max - vari_min)
        return normalized_vari

    def zonal_sum_calculate(self, points, shape, vari):
        segment_mask = self.create_segment_mask(points, shape)
        masked_vari = vari * segment_mask
        pixel_count = np.sum(segment_mask)
        mean_vari = np.sum(masked_vari) 
        return mean_vari, pixel_count

    def height_calculator(self, dem, dem_transform, points, img_transform):
        dem_points = []
        for point in points:
            geo_x, geo_y = rasterio.transform.xy(img_transform, point[1], point[0])
            dem_row, dem_col = rasterio.transform.rowcol(dem_transform, geo_x, geo_y)
            dem_points.append([dem_col, dem_row])
        mask = self.create_segment_mask(dem_points, dem.shape)
        masked_dem = dem[mask == 1]
        if len(masked_dem) == 0:
            return np.nan
        top_values = np.sort(masked_dem.flatten())[-10:]
        return np.mean(top_values)

    def create_segment_mask(self, points, shape):
        mask = np.zeros(shape, dtype=np.uint8)
        poly_points = np.array(points, dtype=np.int32)
        cv2.fillPoly(mask, [poly_points], 1)
        return mask

    def pixel_to_geo(self, pixel, transform):
        x, y = pixel
        geo_x, geo_y = rasterio.transform.xy(transform, y, x, offset='center')
        return geo_x, geo_y

    def save_as_geojson(self, features, output_file):
        geojson = {
            "type": "FeatureCollection",
            "features": features
        }
        with open(output_file, 'w') as f:
            json.dump(geojson, f, indent=4)

    def convert_area_to_pixels(self, area_m2):
        area_cm2 = area_m2 * 10000
        pixel_area_cm2 = self.target_gsd * 100 * self.target_gsd * 100
        return int(area_cm2 / pixel_area_cm2)

    def get_plant_metrics(self, height, pixel_count, vari_score):
        age_ranges = self.reference_areas["tree"]
        estimated_age = None
        health_class = None

        for i in range(len(age_ranges)):
            current = age_ranges[i]
            ref_pixels = self.convert_area_to_pixels(current["canopy_area"])
            
            if i == 0 and height <= current["height"]:
                estimated_age = f"0-{current['age']}"
                ref_height = current["height"]
                reference_pixels = ref_pixels
                break
            
            elif i == len(age_ranges) - 1 and height >= current["height"]:
                estimated_age = f"{current['age']}+"
                ref_height = current["height"]
                reference_pixels = ref_pixels
                break
            
            elif i < len(age_ranges) - 1:
                next_range = age_ranges[i + 1]
                if current["height"] <= height <= next_range["height"]:
                    estimated_age = f"{current['age']}-{next_range['age']}"
                    ref_height = next_range["height"]
                    reference_pixels = self.convert_area_to_pixels(next_range["canopy_area"])
                    break

        if estimated_age:
            height_score = (height / ref_height) * 100
            area_score = (pixel_count / reference_pixels) * 100
            vari_score_percent = vari_score * 100
            
            average_score = (height_score + area_score + vari_score_percent) / 3

            if average_score <= 25:
                health_class = 1
            elif average_score <= 50:
                health_class = 2
            elif average_score <= 75:
                health_class = 3
            else:
                health_class = 4

        return estimated_age, health_class

    def tree_health_calculator(self, image_path, dem_path, json_path, output_file):
        with rasterio.open(image_path) as img_src:
            center_latitude = (img_src.bounds.top + img_src.bounds.bottom) / 2
            original_gsd = self.convert_gsd_to_meters((img_src.transform.a, img_src.transform.e), center_latitude)
            scale_factor = original_gsd[0] / self.target_gsd
            
            rgb_data, rgb_transform = self.resample_raster(img_src, scale_factor)
            new_shape = rgb_data[0].shape

        with rasterio.open(dem_path) as dem_src:
            dem_data, dem_transform = self.resample_raster(dem_src, scale_factor)
            dem = dem_data[0]

        point_label = self.json_loader(json_path)
        vari_array = self.vari_calculator(rgb_data)

        geojson_features = []
        for obj in point_label:
            scaled_points = [[p[0] * scale_factor, p[1] * scale_factor] for p in obj["points"]]
            
            height_meters = self.height_calculator(
                dem=dem,
                dem_transform=dem_transform,
                points=scaled_points,
                img_transform=rgb_transform
            )

            vari_score, pixel_count = self.zonal_sum_calculate(scaled_points, new_shape, vari_array)
            estimated_age, health_class = self.get_plant_metrics(height_meters, pixel_count, vari_score)
            
            geo_coordinates = [self.pixel_to_geo(point, rgb_transform) for point in scaled_points]
            polygon = Polygon(geo_coordinates)

            geojson_features.append({
                "type": "Feature",
                "geometry": mapping(polygon),
                "properties": {
                    "label": obj["label"],
                    "height_meters": float(height_meters) if not np.isnan(height_meters) else None,
                    "vari_score": float(vari_score),
                    "pixel_count": int(pixel_count),
                    "estimated_age": estimated_age,
                    "health_class": int(health_class) if health_class is not None else None
                }
            })

        self.save_as_geojson(geojson_features, output_file)

