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

    def create_styled_vector_layers(self, lines_gdf, wellspace_gdf, segments_gdf):
        """Create styled GeoJSON layers with visualization properties"""
        vector_layers = {
            'type': 'FeatureCollection',
            'features': []
        }

        # Add segments with styling
        for _, segment in segments_gdf.iterrows():
            feature = {
                'type': 'Feature',
                'geometry': segment.geometry.__geo_interface__,
                'properties': {
                    'class': segment['class'],
                    'fillColor': self.health_colors[segment['class']],
                    'fillOpacity': 0.3,
                    'strokeColor': self.health_colors[segment['class']],
                    'strokeWidth': 1,
                    'layerType': 'segment'
                }
            }
            vector_layers['features'].append(feature)

        # Add lines with styling
        for _, line in lines_gdf.iterrows():
            feature = {
                'type': 'Feature',
                'geometry': line.geometry.__geo_interface__,
                'properties': {
                    'class': line['class'],
                    'distance': line['distance'],
                    'strokeColor': self.line_colors[line['class']],
                    'strokeWidth': 2,
                    'strokeOpacity': 0.7,
                    'outlineColor': 'white',
                    'outlineWidth': 3,
                    'layerType': 'line'
                }
            }
            vector_layers['features'].append(feature)

        # Add wellspace points with styling
        for _, point in wellspace_gdf.iterrows():
            feature = {
                'type': 'Feature',
                'geometry': point.geometry.__geo_interface__,
                'properties': {
                    'height_meters': point['height_meters'],
                    'class': point['class'],
                    'pointColor': self.get_point_color(point['height_meters']),
                    'outlineColor': 'white',
                    'outlineRadius': 0.2,
                    'pointRadius': 0.15,
                    'wellSpaced': point['class'] == '1',
                    'layerType': 'wellspace'
                }
            }
            vector_layers['features'].append(feature)

        return vector_layers

    def plot_vector_visualization(self, image_path, lines_geojson_path, wellspace_geojson_path, 
                                segments_geojson_path, output_path, vector_output_path):
        # Read input files
        lines_gdf = gpd.read_file(lines_geojson_path)
        wellspace_gdf = gpd.read_file(wellspace_geojson_path)
        segments_gdf = gpd.read_file(segments_geojson_path)

        # Read and process image
        with rasterio.open(image_path) as src:
            image_crs = src.crs
            if image_crs is None:
                raise ValueError("Image CRS not found. Please ensure the image has a valid CRS.")
            image = src.read()
            bounds = src.bounds
            transform = src.transform
            meta = src.meta.copy()

        # Transform vector layers to image CRS
        lines_gdf_transformed = self.transform_to_image_crs(lines_gdf, image_crs)
        wellspace_gdf_transformed = self.transform_to_image_crs(wellspace_gdf, image_crs)
        segments_gdf_transformed = self.transform_to_image_crs(segments_gdf, image_crs)

        # Create and save styled vector layers
        vector_layers = self.create_styled_vector_layers(
            lines_gdf_transformed, 
            wellspace_gdf_transformed, 
            segments_gdf_transformed
        )
        
        # Save vector layers with styling information
        with open(vector_output_path, 'w') as f:
            json.dump(vector_layers, f, indent=2)

        # Create visualization
        plt.rcParams['figure.dpi'] = 200
        fig, ax = plt.subplots(figsize=(8, 8))

        extent = [bounds.left, bounds.right, bounds.bottom, bounds.top]
        show(image, ax=ax, extent=extent)
        ax.set_xlim([bounds.left, bounds.right])
        ax.set_ylim([bounds.bottom, bounds.top])

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

        # Plot wellspace points
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
        
        # Save the raster visualization
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

# Main execution
def main():
    # Create the visualizer
    viz = TreeVectorViz()
    
    # Set your actual file paths here
    image_path = "your_image.tif"  # Replace with your image path
    lines_path = "your_lines.geojson"  # Replace with your lines geojson
    wellspace_path = "your_wellspace.geojson"  # Replace with your wellspace geojson
    segments_path = "your_segments.geojson"  # Replace with your segments geojson
    
    # Set output paths
    raster_output = "output_visualization.tif"
    vector_output = "output_styled_vectors.geojson"
    
    print("Starting visualization process...")
    print(f"Reading input files from: {image_path}")
    
    try:
        # Run the visualization
        viz.plot_vector_visualization(
            r"C:\Users\User\Downloads\1627_utm_checked\1627_utm_checked\1627_utm\P2_35A_imagesRGB_orthomosaic.tif", 
            r"C:\Users\User\Downloads\1627_utm_checked\1627_utm_checked\Results\Line_Geojsons\P2_35A_imagesRGB_orthomosaic.geojson",
            r"C:\Users\User\Downloads\1627_utm_checked\1627_utm_checked\Results\WellSpace_Geojsons\P2_35A_imagesRGB_orthomosaic.geojson",
            r"C:\Users\User\Downloads\1627_utm_checked\1627_utm_checked\Results\Health_Results\P2_35A_imagesRGB_orthomosaic.geojson",
            r"C:\Users\User\Downloads\1627_utm_checked\1627_utm_checked\Results\output.tif",
            r"C:\Users\User\Downloads\1627_utm_checked\1627_utm_checked\Results\styled.geojson"
        )
        
        print(f"Successfully created visualization!")
        print(f"Raster output saved to: {raster_output}")
        print(f"Vector output saved to: {vector_output}")
        
    except Exception as e:
        print(f"Error occurred during visualization: {str(e)}")
        raise

if __name__ == "__main__":
    main()


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