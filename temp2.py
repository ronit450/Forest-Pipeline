import geopandas as gpd
import matplotlib.pyplot as plt
import matplotlib.patheffects as path_effects
import numpy as np
from matplotlib.patches import Circle, Polygon
import rasterio
from rasterio.plot import show
from pyproj import CRS
from osgeo import gdal, ogr
import os
import tempfile

class TreeVectorViz:
    def __init__(self):
        self.health_colors = {0: '#E3412B', 1: '#FBAA35', 2: '#30C876', 3: '#1E8C4D'}
        self.line_colors = {0: 'red', 1: 'yellow', 2: 'green'}
        gdal.AllRegister()

    def get_point_color(self, height):
        if height <= 1.5:
            return 'orange'
        if height <= 2.5:
            return 'yellow'
        return 'lime'

    def transform_to_image_crs(self, gdf, image_crs):
        """Transform GeoDataFrame from WGS84 to image's CRS"""
        if gdf.crs is None:
            gdf.set_crs(epsg=4326, inplace=True)
        return gdf.to_crs(image_crs)

    def create_separate_layers(self, image_crs, segments_gdf, lines_gdf, wellspace_gdf, temp_dir):
        """Create separate GeoJSON files for each layer"""
        # Transform to image CRS
        segments_transformed = self.transform_to_image_crs(segments_gdf, image_crs)
        lines_transformed = self.transform_to_image_crs(lines_gdf, image_crs)
        wellspace_transformed = self.transform_to_image_crs(wellspace_gdf, image_crs)

        # Save transformed layers
        segments_path = os.path.join(temp_dir, "segments.geojson")
        lines_path = os.path.join(temp_dir, "lines.geojson")
        points_path = os.path.join(temp_dir, "points.geojson")

        segments_transformed.to_file(segments_path, driver='GeoJSON')
        lines_transformed.to_file(lines_path, driver='GeoJSON')
        wellspace_transformed.to_file(points_path, driver='GeoJSON')

        return segments_path, lines_path, points_path

    def create_layered_pdf(self, image_path, geojson_paths, output_pdf):
        """Create PDF with toggleable layers"""
        try:
            # Create VRT for the image
            vrt_path = "temp_base.vrt"
            gdal.BuildVRT(vrt_path, [image_path])

            # Initial translation to PDF with base image
            pdf_options = [
                'MARGIN=0',
                'DPI=300',
                'GEO_ENCODING=ISO32000',
                'LAYER_NAME=Image',
                'EXTRA_STREAM=LAYERS',
                'EXTRA_STREAM=TRANSPARENCY'
            ]

            gdal.Translate(output_pdf, vrt_path, format='PDF', 
                          creationOptions=pdf_options)

            # Add each vector layer
            layer_names = ['Segments', 'Connections', 'Trees']
            for layer_name, geojson_path in zip(layer_names, geojson_paths):
                # Create new options for each layer
                ogr_options = gdal.VectorTranslateOptions(
                    format='PDF',
                    layerName=layer_name,
                    datasetCreationOptions=['APPEND_LAYERS=TRUE'],
                    accessMode='update'
                )
                
                # Open source dataset
                src_ds = gdal.OpenEx(geojson_path, gdal.OF_VECTOR)
                if src_ds is None:
                    print(f"Could not open {geojson_path}")
                    continue

                # Add layer to PDF
                gdal.VectorTranslate(
                    output_pdf,
                    src_ds,
                    options=ogr_options
                )
                
                # Clean up
                src_ds = None

        finally:
            # Clean up VRT
            if os.path.exists(vrt_path):
                os.remove(vrt_path)

    def plot_vector_visualization(self, image_path, lines_geojson_path, wellspace_geojson_path, 
                                segments_geojson_path, output_path):
        # Read the vector data
        lines_gdf = gpd.read_file(lines_geojson_path)
        wellspace_gdf = gpd.read_file(wellspace_geojson_path)
        segments_gdf = gpd.read_file(segments_geojson_path)

        # Get image metadata
        with rasterio.open(image_path) as src:
            image_crs = src.crs
            if image_crs is None:
                raise ValueError("Image CRS not found. Please ensure the image has a valid CRS.")
            image = src.read()
            bounds = src.bounds
            transform = src.transform
            meta = src.meta.copy()

        # Create and manage temporary files
        try:
            # Create temporary directory
            temp_dir = tempfile.mkdtemp()
            
            # Create separate layer files
            layer_paths = self.create_separate_layers(
                image_crs, segments_gdf, lines_gdf, wellspace_gdf, temp_dir
            )
            
            # Create layered PDF
            pdf_output = output_path.replace('.tiff', '.pdf')
            self.create_layered_pdf(image_path, layer_paths, pdf_output)

        finally:
            # Clean up temporary files
            try:
                for file in os.listdir(temp_dir):
                    file_path = os.path.join(temp_dir, file)
                    if os.path.isfile(file_path):
                        os.unlink(file_path)
                os.rmdir(temp_dir)
            except Exception as e:
                print(f"Error cleaning up temporary files: {str(e)}")
                pass  # Continue even if cleanup fails

        # Create visualization TIFF as before
        # Set up the figure
        plt.rcParams['figure.dpi'] = 300
        fig, ax = plt.subplots(figsize=(12, 12))

        # Plot the base image
        extent = [bounds.left, bounds.right, bounds.bottom, bounds.top]
        show(image, ax=ax, extent=extent)
        ax.set_xlim([bounds.left, bounds.right])
        ax.set_ylim([bounds.bottom, bounds.top])

        # Transform geodataframes
        lines_gdf_transformed = self.transform_to_image_crs(lines_gdf, image_crs)
        wellspace_gdf_transformed = self.transform_to_image_crs(wellspace_gdf, image_crs)
        segments_gdf_transformed = self.transform_to_image_crs(segments_gdf, image_crs)

        # Plot segments
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

        # Plot lines
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
            offset = 0.15
            offset_x = -dy / line_length * offset
            offset_y = dx / line_length * offset

            ax.text(mid_x + offset_x, mid_y + offset_y, 
                   f'{distance:.2f}m',
                   color='white',
                   fontsize=8,
                   fontweight='bold',
                   ha='center',
                   va='center',
                   rotation=angle,
                   path_effects=[path_effects.withStroke(linewidth=3, foreground='black')],
                   zorder=4)

        # Plot points
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
            
            if well_spaced == 1:
                ax.add_patch(Circle(
                    (x, y),
                    0.07,
                    color='black',
                    zorder=7
                ))
            
            ax.text(x, y + 0.3,
                   f'{height:.2f}m',
                   color='white',
                   fontsize=8,
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

        # Save visualization
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



if __name__ == "__main__":
    visualizer = TreeVectorViz()
    visualizer.plot_vector_visualization(
        r"C:\Users\User\Downloads\1627_utm_checked\1627_utm_checked\1627_utm\P2_32B_imagesRGB_orthomosaic.tif", 
        r"C:\Users\User\Downloads\1627_utm_checked\1627_utm_checked\Results\Line_Geojsons\P2_32B_imagesRGB_orthomosaic.geojson", 
        r"C:\Users\User\Downloads\1627_utm_checked\1627_utm_checked\Results\WellSpace_Geojsons\P2_32B_imagesRGB_orthomosaic.geojson",
        r"C:\Users\User\Downloads\1627_utm_checked\1627_utm_checked\Results\Health_Results\P2_32B_imagesRGB_orthomosaic.geojson", 
        'output.tiff'
    )