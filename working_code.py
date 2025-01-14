import geopandas as gpd
from osgeo import gdal, ogr, osr
import os
import math

class ShapefileToPDF:
    def __init__(self):
        self.health_colors = {'0': '#E3412B', '1': '#FBAA35', '2': '#30C876', '3': '#1E8C4D'}
        self.line_colors = {'0': '#3EBCA1', '1': '#D9D9D9', '2': '#FD3E3E'}
    
    def get_point_color(self, height):
        if height <= 1.5:
            return 'orange'
        if height <= 2.5:
            return 'yellow'
        return 'lime'
    
    def process_tiff_layer(self, input_tiff, pdf_ds, srs):
        """
        Adds a georeferenced TIFF as a base layer in the PDF with improved handling
        """
        # Create raster layer
        tiff_layer = pdf_ds.CreateLayer('Base_Imagery', srs, ogr.wkbUnknown,
                                    options=['LAYER_NAME=Base Imagery'])
        
        # Open and validate the TIFF file
        src_ds = gdal.Open(input_tiff)
        if src_ds is None:
            raise Exception(f"Could not open TIFF file: {input_tiff}")

        # Get source SRS
        src_srs = osr.SpatialReference()
        src_wkt = src_ds.GetProjection()
        if src_wkt:
            src_srs.ImportFromWkt(src_wkt)
        
        # Create transformation if needed
        transform = None
        if src_srs and not src_srs.IsSame(srs):
            transform = osr.CoordinateTransformation(src_srs, srs)
        
        # Get the geotransform
        gt = src_ds.GetGeoTransform()
        
        # Get raster dimensions
        width = src_ds.RasterXSize
        height = src_ds.RasterYSize
        
        # Calculate corner coordinates
        corners = [
            (0, 0),                    # Top left
            (width, 0),                # Top right
            (width, height),           # Bottom right
            (0, height),               # Bottom left
            (0, 0)                     # Close the ring
        ]
        
        # Create ring geometry
        ring = ogr.Geometry(ogr.wkbLinearRing)
        
        # Add transformed coordinates to ring
        for x, y in corners:
            # Convert pixel coordinates to geo coordinates
            geo_x = gt[0] + x * gt[1] + y * gt[2]
            geo_y = gt[3] + x * gt[4] + y * gt[5]
            
            # Transform coordinates if needed
            if transform:
                geo_x, geo_y, _ = transform.TransformPoint(geo_x, geo_y)
                
            ring.AddPoint(geo_x, geo_y)
        
        # Create polygon from ring
        polygon = ogr.Geometry(ogr.wkbPolygon)
        polygon.AddGeometry(ring)
        
        # Create feature
        feature = ogr.Feature(tiff_layer.GetLayerDefn())
        feature.SetGeometry(polygon)
        
        # Set raster styling with world file parameters
        style = (
            f'RASTER({input_tiff},'
            f'WORLDFILE=YES,'
            f'ALPHA=75)'  # 75% opacity
        )
        
        feature.SetStyleString(style)
        tiff_layer.CreateFeature(feature)
        
        src_ds = None


    def create_pdf_layers(self, input_dir, output_pdf, tiff_path):
        """
        Create georeferenced PDF with layers including optional TIFF base layer
        """
        # Configure GDAL
        gdal.SetConfigOption('OGR_PDF_LAYER_CREATION_OPTIONS', 'ON')
        gdal.SetConfigOption('OGR_PDF_INCLUDE_LAYER_NAMES', 'ON')
        gdal.SetConfigOption('GDAL_PDF_BANDS', '4')
        gdal.SetConfigOption('OGR_PDF_GEO_ENCODING', 'ISO32000')
        
        # Set up the spatial reference system
        srs = osr.SpatialReference()
        srs.ImportFromEPSG(32610)  # UTM Zone 10N
        
        driver = ogr.GetDriverByName('PDF')
        options = [
            'PDF_LAYER_ORDER=ON',
            'OGR_PDF_WRITE_INFO=ON',
            'DPI=300',
            'EXTRA_STREAM=OPACITY:1',
            'COMPOSITION=AUTO',
            'MARGIN=0',
            'CLUSTER_KMEANS=OFF',
            'GEO_ENCODING=ISO32000',
            'NEATLINE=NO'
        ]
        
        # Add spatial reference to options
        options.append(f'SPATIAL_REF_SYS_WKT={srs.ExportToWkt()}')
        
        # If we have a TIFF, use its extent for the PDF
        if tiff_path:
            tiff_ds = gdal.Open(tiff_path)
            if tiff_ds:
                gt = tiff_ds.GetGeoTransform()
                width = tiff_ds.RasterXSize
                height = tiff_ds.RasterYSize
                
                # Calculate extent
                minx = gt[0]
                maxx = gt[0] + gt[1] * width
                miny = gt[3] + gt[5] * height
                maxy = gt[3]
                
                # Add extent to options
                options.extend([
                    f'BBOX={minx},{miny},{maxx},{maxy}',
                    f'IMAGE_EXTENT={minx},{miny},{maxx},{maxy}'
                ])
                
                tiff_ds = None
        
        pdf_ds = driver.CreateDataSource(output_pdf, options=options)
        
        # Add TIFF base layer first if provided
        if tiff_path:
            try:
                self.process_tiff_layer(tiff_path, pdf_ds, srs)
            except Exception as e:
                print(f"Warning: Failed to process TIFF layer: {str(e)}")
        
        # Process other layers
        self.process_segments(input_dir, pdf_ds, srs)
        self.process_lines(input_dir, pdf_ds, srs)
        self.process_points(input_dir, pdf_ds, srs)
        self.process_toggle_points(input_dir, pdf_ds, srs)
        
        # Create label layers
        self.create_line_labels(input_dir, pdf_ds, srs)
        self.create_point_labels(input_dir, pdf_ds, srs)
        
        pdf_ds = None



    
    def process_toggle_points(self, input_dir, pdf_ds, srs):
        """
        Creates a separate layer for toggle points where class 1 points are shown as small grey circles
        """
        toggle_points_layer = pdf_ds.CreateLayer('Well-Space', srs, ogr.wkbPoint,
                                            options=['LAYER_NAME=Toggle Points'])
        
        points_shp = os.path.join(input_dir, 'points.shp')
        points_ds = ogr.Open(points_shp)
        points_src = points_ds.GetLayer()
        
        # Create fields
        class_field = ogr.FieldDefn('class', ogr.OFTString)
        toggle_points_layer.CreateField(class_field)
        
        # Copy features and style based on class
        for feature in points_src:
            class_val = feature.GetField('class')
            
            # Only process points with class = 1
            if str(class_val) == '1':
                out_feature = ogr.Feature(toggle_points_layer.GetLayerDefn())
                out_feature.SetGeometry(feature.GetGeometryRef().Clone())
                out_feature.SetField('class', str(class_val))
                
                # Style with small grey circle
                style = (
                    f'SYMBOL(id:circle,c:#808080,s:0.5pt)'  # Grey circle with 0.5pt size
                )
                
                out_feature.SetStyleString(style)
                toggle_points_layer.CreateFeature(out_feature)
        
        points_ds = None
    

    def process_segments(self, input_dir, pdf_ds, srs):
        segments_layer = pdf_ds.CreateLayer('Segments', srs, ogr.wkbPolygon,
                                          options=['LAYER_NAME=Segments'])
        
        segments_shp = os.path.join(input_dir, 'segments.shp')
        segments_ds = ogr.Open(segments_shp)
        segments_src = segments_ds.GetLayer()
        
        # Create fields
        class_field = ogr.FieldDefn('class', ogr.OFTString)
        segments_layer.CreateField(class_field)
        
        # Copy features
        for feature in segments_src:
            out_feature = ogr.Feature(segments_layer.GetLayerDefn())
            out_feature.SetGeometry(feature.GetGeometryRef().Clone())
            class_val = feature.GetField('class')
            out_feature.SetField('class', str(class_val))
            out_feature.SetStyleString(f'BRUSH(fc:{self.health_colors[str(class_val)]},bc:#000000);PEN(c:#000000,w:0.1pt)')
            segments_layer.CreateFeature(out_feature)
        
        segments_ds = None
    
    def process_lines(self, input_dir, pdf_ds, srs):
        lines_layer = pdf_ds.CreateLayer('Lines', srs, ogr.wkbLineString,
                                       options=['LAYER_NAME=Lines'])
        
        lines_shp = os.path.join(input_dir, 'lines.shp')
        lines_ds = ogr.Open(lines_shp)
        lines_src = lines_ds.GetLayer()
        
        # Create fields
        class_field = ogr.FieldDefn('class', ogr.OFTString)
        distance_field = ogr.FieldDefn('distance', ogr.OFTReal)
        lines_layer.CreateField(class_field)
        lines_layer.CreateField(distance_field)
        
        # Copy features
        for feature in lines_src:
            out_feature = ogr.Feature(lines_layer.GetLayerDefn())
            out_feature.SetGeometry(feature.GetGeometryRef().Clone())
            class_val = str(feature.GetField('class'))
            distance = feature.GetField('distance')
            out_feature.SetField('class', class_val)
            out_feature.SetField('distance', distance)
            out_feature.SetStyleString(f'PEN(c:{self.line_colors[class_val]},w:2pt)')
            lines_layer.CreateFeature(out_feature)
        
        lines_ds = None
    

    def process_points(self, input_dir, pdf_ds, srs):
        points_layer = pdf_ds.CreateLayer('Points', srs, ogr.wkbPoint,
                                        options=['LAYER_NAME=Points'])
        
        points_shp = os.path.join(input_dir, 'points.shp')
        points_ds = ogr.Open(points_shp)
        points_src = points_ds.GetLayer()
        
        # Create fields
        class_field = ogr.FieldDefn('class', ogr.OFTString)
        height_field = ogr.FieldDefn('height_m', ogr.OFTReal)
        points_layer.CreateField(class_field)
        points_layer.CreateField(height_field)
        
        # Copy features
        for feature in points_src:
            out_feature = ogr.Feature(points_layer.GetLayerDefn())
            out_feature.SetGeometry(feature.GetGeometryRef().Clone())
            height = feature.GetField('height_m')
            class_val = feature.GetField('class')
            
            # Get color from height
            if height <= 1.5:
                point_color = '#FD8D5A'    # Orange-red
            elif height <= 2.5:
                point_color = '#FFD551'    # Yellow
            else:
                point_color = '#32CD32'  # darker green
            
            out_feature.SetField('class', str(class_val))
            out_feature.SetField('height_m', height)
            
            # Style points using BRUSH for fill and PEN for border
            style = (
                f'BRUSH(fc:{point_color});'  # Fill color
                f'PEN(c:#FFFFFF,w:1.5pt);'     # White border
                f'SYMBOL(id:circle,s:1.5pt)'    # Symbol size
            )
            
            out_feature.SetStyleString(style)
            points_layer.CreateFeature(out_feature)
        
        points_ds = None
                
         
    def create_line_labels(self, input_dir, pdf_ds, srs):
        label_layer = pdf_ds.CreateLayer('Line_Labels', srs, ogr.wkbPoint,
                                       options=['LAYER_NAME=Line Distances'])
        
        lines_shp = os.path.join(input_dir, 'lines.shp')
        lines_ds = ogr.Open(lines_shp)
        lines_src = lines_ds.GetLayer()
        
        label_field = ogr.FieldDefn('label_text', ogr.OFTString)
        label_layer.CreateField(label_field)
        
        for feature in lines_src:
            geom = feature.GetGeometryRef()
            distance = feature.GetField('distance')
            
            # Get points to calculate angle
            points = geom.GetPoints()
            if len(points) >= 2:
                start_point = points[0]
                end_point = points[-1]
                
                # Calculate midpoint
                mid_x = (start_point[0] + end_point[0]) / 2
                mid_y = (start_point[1] + end_point[1]) / 2
                
                # Calculate angle in degrees
                dx = end_point[0] - start_point[0]
                dy = end_point[1] - start_point[1]
                angle = math.degrees(math.atan2(dy, dx))
                
                # Adjust angle to keep text readable (not upside down)
                if angle < -90 or angle > 90:
                    angle += 180
                
                # Create point geometry for label
                point = ogr.Geometry(ogr.wkbPoint)
                point.AddPoint(mid_x, mid_y)
                
                out_feature = ogr.Feature(label_layer.GetLayerDefn())
                out_feature.SetGeometry(point)
                label_text = f'{distance:.1f}m'
                out_feature.SetField('label_text', label_text)
                
                # Add angle to label style
                style = f'LABEL(f:"Arial",s:10pt,t:{label_text},c:#000000,a:{angle:.1f})'
                out_feature.SetStyleString(style)
                label_layer.CreateFeature(out_feature)
        
        lines_ds = None
    
    def create_point_labels(self, input_dir, pdf_ds, srs):
        label_layer = pdf_ds.CreateLayer('Point_Labels', srs, ogr.wkbPoint,
                                       options=['LAYER_NAME=Point Heights'])
        
        points_shp = os.path.join(input_dir, 'points.shp')
        points_ds = ogr.Open(points_shp)
        points_src = points_ds.GetLayer()
        
        label_field = ogr.FieldDefn('label_text', ogr.OFTString)
        label_layer.CreateField(label_field)
        
        for feature in points_src:
            out_feature = ogr.Feature(label_layer.GetLayerDefn())
            out_feature.SetGeometry(feature.GetGeometryRef().Clone())
            height = feature.GetField('height_m')
            # Enhanced label style with bold text and background halo
            label_text = f'{height:.1f}m'
            out_feature.SetField('label_text', label_text)
            out_feature.SetStyleString(f'LABEL(f:"Arial Bold",s:8pt,t:{label_text},c:#000000,dx:6,dy:3,bo:#FFFFFF,hc:#FFFFFF,ho:2.5)')
            label_layer.CreateFeature(out_feature)
        
        points_ds = None

if __name__ == "__main__":
    converter = ShapefileToPDF()
    input_directory = r"C:\Users\User\Downloads\1627_utm_checked\1627_utm_checked\Results\vectors"
    output_pdf = "output_layers_with_tiff.pdf"
    tiff_path = r"C:\Users\User\Downloads\1627_utm_checked\1627_utm_checked\1627_utm\P2_35A_imagesRGB_orthomosaic.tif"
    converter.create_pdf_layers(input_directory, output_pdf, tiff_path)