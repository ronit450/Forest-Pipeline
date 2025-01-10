import numpy as np
import geopandas as gpd
import matplotlib.pyplot as plt
from matplotlib.patches import Circle
import rasterio
from rasterio.plot import show
import json

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

    def create_styled_vector_layers(self, lines_gdf, wellspace_gdf, segments_gdf, output_dir):
        """Create styled shapefiles with visualization properties"""
        from osgeo import ogr, osr
        import os
        
        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)
        
        # Create driver
        driver = ogr.GetDriverByName('ESRI Shapefile')
        
        # Set spatial reference (UTM Zone 10N)
        srs = osr.SpatialReference()
        srs.ImportFromEPSG(32610)
        
        # Create segment shapefile
        segment_ds = driver.CreateDataSource(os.path.join(output_dir, 'segments.shp'))
        segment_layer = segment_ds.CreateLayer('segments', srs, ogr.wkbPolygon)
        
        # Add fields for segments
        segment_layer.CreateField(ogr.FieldDefn('class', ogr.OFTString))
        segment_layer.CreateField(ogr.FieldDefn('fillColor', ogr.OFTString))
        segment_layer.CreateField(ogr.FieldDefn('strokeCol', ogr.OFTString))
        segment_layer.CreateField(ogr.FieldDefn('opacity', ogr.OFTReal))
        
        # Create lines shapefile
        line_ds = driver.CreateDataSource(os.path.join(output_dir, 'lines.shp'))
        line_layer = line_ds.CreateLayer('lines', srs, ogr.wkbLineString)
        
        # Add fields for lines
        line_layer.CreateField(ogr.FieldDefn('class', ogr.OFTString))
        line_layer.CreateField(ogr.FieldDefn('distance', ogr.OFTReal))
        line_layer.CreateField(ogr.FieldDefn('strokeCol', ogr.OFTString))
        
        # Create points shapefile
        point_ds = driver.CreateDataSource(os.path.join(output_dir, 'points.shp'))
        point_layer = point_ds.CreateLayer('points', srs, ogr.wkbPoint)
        
        # Add fields for points
        point_layer.CreateField(ogr.FieldDefn('class', ogr.OFTString))
        point_layer.CreateField(ogr.FieldDefn('height_m', ogr.OFTReal))
        point_layer.CreateField(ogr.FieldDefn('pointCol', ogr.OFTString))
        
        # Add segments
        for _, segment in segments_gdf.iterrows():
            feature = ogr.Feature(segment_layer.GetLayerDefn())
            geom = ogr.CreateGeometryFromWkt(segment.geometry.wkt)
            feature.SetGeometry(geom)
            feature.SetField('class', str(segment['class']))
            feature.SetField('fillColor', self.health_colors[segment['class']])
            feature.SetField('strokeCol', self.health_colors[segment['class']])
            feature.SetField('opacity', 0.3)
            segment_layer.CreateFeature(feature)
        
        # Add lines
        for _, line in lines_gdf.iterrows():
            feature = ogr.Feature(line_layer.GetLayerDefn())
            geom = ogr.CreateGeometryFromWkt(line.geometry.wkt)
            feature.SetGeometry(geom)
            feature.SetField('class', str(line['class']))
            feature.SetField('distance', float(line['distance']))
            feature.SetField('strokeCol', self.line_colors[line['class']])
            line_layer.CreateFeature(feature)
        
        # Add points
        for _, point in wellspace_gdf.iterrows():
            feature = ogr.Feature(point_layer.GetLayerDefn())
            geom = ogr.CreateGeometryFromWkt(point.geometry.wkt)
            feature.SetGeometry(geom)
            feature.SetField('class', str(point['class']))
            feature.SetField('height_m', float(point['height_meters']))
            feature.SetField('pointCol', self.get_point_color(point['height_meters']))
            point_layer.CreateFeature(feature)
        
        # Clean up
        segment_ds = None
        line_ds = None
        point_ds = None

        return os.path.join(output_dir, 'segments.shp'), os.path.join(output_dir, 'lines.shp'), os.path.join(output_dir, 'points.shp')


    def plot_vector_visualization(self, image_path, lines_geojson_path, wellspace_geojson_path, 
                                segments_geojson_path, output_path, vector_output_dir):
        # Read input files
        lines_gdf = gpd.read_file(lines_geojson_path)
        wellspace_gdf = gpd.read_file(wellspace_geojson_path)
        segments_gdf = gpd.read_file(segments_geojson_path)

        # Read and process image
        with rasterio.open(image_path) as src:
            image_crs = src.crs
            if image_crs is None:
                raise ValueError("Image CRS not found. Please ensure the image has a valid CRS.")
            
        # Transform vector layers to image CRS
        lines_gdf_transformed = self.transform_to_image_crs(lines_gdf, image_crs)
        wellspace_gdf_transformed = self.transform_to_image_crs(wellspace_gdf, image_crs)
        segments_gdf_transformed = self.transform_to_image_crs(segments_gdf, image_crs)

        # Create shapefiles
        segments_shp, lines_shp, points_shp = self.create_styled_vector_layers(
            lines_gdf_transformed, 
            wellspace_gdf_transformed, 
            segments_gdf_transformed,
            vector_output_dir
        )
        
        print(f"Created shapefiles at:")
        print(f"Segments: {segments_shp}")
        print(f"Lines: {lines_shp}")
        print(f"Points: {points_shp}")

# # Main execution
# def main():
#     # Create the visualizer
#     viz = TreeVectorViz()
    
#     # Set your actual file paths here
#     image_path = "your_image.tif"  # Replace with your image path
#     lines_path = "your_lines.geojson"  # Replace with your lines geojson
#     wellspace_path = "your_wellspace.geojson"  # Replace with your wellspace geojson
#     segments_path = "your_segments.geojson"  # Replace with your segments geojson
    
#     # Set output paths
#     raster_output = "output_visualization.tif"
#     vector_output = "output_styled_vectors.geojson"
    
#     print("Starting visualization process...")
#     print(f"Reading input files from: {image_path}")
    
#     try:
#         # Run the visualization
#         viz.plot_vector_visualization(
#             r"C:\Users\User\Downloads\1627_utm_checked\1627_utm_checked\1627_utm\P2_35A_imagesRGB_orthomosaic.tif", 
#             r"C:\Users\User\Downloads\1627_utm_checked\1627_utm_checked\Results\Line_Geojsons\P2_35A_imagesRGB_orthomosaic.geojson",
#             r"C:\Users\User\Downloads\1627_utm_checked\1627_utm_checked\Results\WellSpace_Geojsons\P2_35A_imagesRGB_orthomosaic.geojson",
#             r"C:\Users\User\Downloads\1627_utm_checked\1627_utm_checked\Results\Health_Results\P2_35A_imagesRGB_orthomosaic.geojson",
#             r"C:\Users\User\Downloads\1627_utm_checked\1627_utm_checked\Results\output.tif",
#             r"C:\Users\User\Downloads\1627_utm_checked\1627_utm_checked\Results\styled.geojson"
#         )
        
#         print(f"Successfully created visualization!")
#         print(f"Raster output saved to: {raster_output}")
#         print(f"Vector output saved to: {vector_output}")
        
#     except Exception as e:
#         print(f"Error occurred during visualization: {str(e)}")
#         raise

if __name__ == "__main__":
    visualizer = TreeVectorViz()
    visualizer.plot_vector_visualization(
        r"C:\Users\User\Downloads\1627_utm_checked\1627_utm_checked\1627_utm\P2_35A_imagesRGB_orthomosaic.tif", 
        r"C:\Users\User\Downloads\1627_utm_checked\1627_utm_checked\Results\Line_Geojsons\P2_35A_imagesRGB_orthomosaic.geojson",
        r"C:\Users\User\Downloads\1627_utm_checked\1627_utm_checked\Results\WellSpace_Geojsons\P2_35A_imagesRGB_orthomosaic.geojson",
        r"C:\Users\User\Downloads\1627_utm_checked\1627_utm_checked\Results\Health_Results\P2_35A_imagesRGB_orthomosaic.geojson",
        'output.tif',
        r"C:\Users\User\Downloads\1627_utm_checked\1627_utm_checked\Results\vectors"
    )


# if __name__ == "__main__":

#     visualizer = TreeVectorViz()
#     visualizer.plot_vector_visualization(
#         r"C:\Users\User\Downloads\1627_utm_checked\1627_utm_checked\1627_utm\P2_35A_imagesRGB_orthomosaic.tif", 
#         r"C:\Users\User\Downloads\1627_utm_checked\1627_utm_checked\Results\Line_Geojsons\P2_35A_imagesRGB_orthomosaic.geojson",
#         r"C:\Users\User\Downloads\1627_utm_checked\1627_utm_checked\Results\WellSpace_Geojsons\P2_35A_imagesRGB_orthomosaic.geojson",
#         r"C:\Users\User\Downloads\1627_utm_checked\1627_utm_checked\Results\Health_Results\P2_35A_imagesRGB_orthomosaic.geojson",
#         'output.tif',
#         'styled.geojson' 
        
#     )