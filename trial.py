from osgeo import gdal, ogr, osr
import os
import math
import numpy as np
from PIL import Image

def create_georeferenced_logo(input_tiff, logo_path, output_dir, logo_size=(20, 20)):
    """Create a georeferenced logo overlay"""
    # Get input TIFF information
    ds = gdal.Open(input_tiff)
    gt = ds.GetGeoTransform()
    proj = ds.GetProjection()
    width = ds.RasterXSize
    height = ds.RasterYSize
    
    # Calculate position (top-right with padding)
    padding = 40  # pixels from edge
    pixel_x = width - padding - logo_size[0]
    pixel_y = padding
    
    # Convert to georeferenced coordinates
    geo_x = gt[0] + pixel_x * gt[1]
    geo_y = gt[3] + pixel_y * gt[5]
    
    # Create logo overlay
    logo = Image.open(logo_path)
    if logo.mode != 'RGBA':
        logo = logo.convert('RGBA')
    logo = logo.resize(logo_size, Image.Resampling.LANCZOS)
    
    # Create new georeferenced raster
    logo_tiff = os.path.join(output_dir, 'logo_overlay.tif')
    driver = gdal.GetDriverByName('GTiff')
    
    # Create output raster with 4 bands (RGBA)
    out_ds = driver.Create(logo_tiff, logo_size[0], logo_size[1], 4, gdal.GDT_Byte)
    
    # Set the geotransform and projection
    new_gt = (geo_x, gt[1], gt[2], geo_y, gt[4], gt[5])
    out_ds.SetGeoTransform(new_gt)
    out_ds.SetProjection(proj)
    
    # Convert PIL image to numpy array and write to bands
    logo_array = np.array(logo)
    for i in range(4):  # Write each RGBA band
        band = out_ds.GetRasterBand(i + 1)
        band.WriteArray(logo_array[:, :, i])
    
    out_ds.FlushCache()
    out_ds = None
    ds = None
    
    return logo_tiff
    
    

def modify_segments_style(input_dir):
    """Modify segments shapefile style"""
    health_colors = {'0': '#E3412B', '1': '#FBAA35', '2': '#30C876', '3': '#1E8C4D'}
    
    segments_shp = os.path.join(input_dir, 'segments.shp')
    ds = ogr.Open(segments_shp, 1)
    layer = ds.GetLayer()
    
    try:
        layer.CreateField(ogr.FieldDefn('OGR_STYLE', ogr.OFTString))
    except:
        pass
    
    for feature in layer:
        class_val = str(feature.GetField('class'))
        if class_val in health_colors:
            style_string = f'BRUSH(fc:{health_colors[class_val]});PEN(c:#000000,w:0.1pt)'
            feature.SetField('OGR_STYLE', style_string)
            layer.SetFeature(feature)
    
    ds = None

def modify_lines_style(input_dir):
    """Modify lines shapefile style"""
    line_colors = {'0': '#3EBCA1', '1': '#D9D9D9', '2': '#FD3E3E'}
    
    lines_shp = os.path.join(input_dir, 'lines.shp')
    ds = ogr.Open(lines_shp, 1)
    layer = ds.GetLayer()
    
    try:
        layer.CreateField(ogr.FieldDefn('OGR_STYLE', ogr.OFTString))
    except:
        pass
    
    for feature in layer:
        class_val = str(feature.GetField('class'))
        if class_val in line_colors:
            style_string = f'PEN(c:{line_colors[class_val]},w:2pt)'
            feature.SetField('OGR_STYLE', style_string)
            layer.SetFeature(feature)
    
    ds = None

def modify_points_style(input_dir):
    """Modify points shapefile style"""
    points_shp = os.path.join(input_dir, 'points.shp')
    ds = ogr.Open(points_shp, 1)
    layer = ds.GetLayer()
    
    try:
        layer.CreateField(ogr.FieldDefn('OGR_STYLE', ogr.OFTString))
    except:
        pass
    
    for feature in layer:
        height = feature.GetField('height_m')
        
        if height <= 1.5:
            point_color = '#FD8D5A'
        elif height <= 2.5:
            point_color = '#FFD551'
        else:
            point_color = '#32CD32'
        
        style_string = (
            f'SYMBOL(id:circle,c:{point_color},s:1.5pt);'
            'PEN(c:#FFFFFF,w:1.5pt)'
        )
        feature.SetField('OGR_STYLE', style_string)
        layer.SetFeature(feature)
    
    ds = None

def create_well_space_points(input_dir):
    """Create well-space points layer from points with class 1"""
    points_shp = os.path.join(input_dir, 'points.shp')
    well_space_shp = os.path.join(input_dir, 'well_space.shp')
    
    driver = ogr.GetDriverByName('ESRI Shapefile')
    if os.path.exists(well_space_shp):
        driver.DeleteDataSource(well_space_shp)
    
    out_ds = driver.CreateDataSource(well_space_shp)
    out_layer = out_ds.CreateLayer('well_space', geom_type=ogr.wkbPoint)
    
    class_field = ogr.FieldDefn('class', ogr.OFTString)
    style_field = ogr.FieldDefn('OGR_STYLE', ogr.OFTString)
    out_layer.CreateField(class_field)
    out_layer.CreateField(style_field)
    
    points_ds = ogr.Open(points_shp)
    points_layer = points_ds.GetLayer()
    
    for feature in points_layer:
        if str(feature.GetField('class')) == '1':
            out_feature = ogr.Feature(out_layer.GetLayerDefn())
            out_feature.SetGeometry(feature.GetGeometryRef().Clone())
            out_feature.SetField('class', '1')
            out_feature.SetField('OGR_STYLE', 'SYMBOL(id:circle,c:#808080,s:0.5pt)')
            out_layer.CreateFeature(out_feature)
    
    points_ds = None
    out_ds = None

def create_point_labels(input_dir):
    """Create point labels layer"""
    points_shp = os.path.join(input_dir, 'points.shp')
    labels_shp = os.path.join(input_dir, 'point_labels.shp')
    
    driver = ogr.GetDriverByName('ESRI Shapefile')
    if os.path.exists(labels_shp):
        driver.DeleteDataSource(labels_shp)
    
    out_ds = driver.CreateDataSource(labels_shp)
    out_layer = out_ds.CreateLayer('point_labels', geom_type=ogr.wkbPoint)
    
    label_field = ogr.FieldDefn('label', ogr.OFTString)
    style_field = ogr.FieldDefn('OGR_STYLE', ogr.OFTString)
    out_layer.CreateField(label_field)
    out_layer.CreateField(style_field)
    
    points_ds = ogr.Open(points_shp)
    points_layer = points_ds.GetLayer()
    
    for feature in points_layer:
        out_feature = ogr.Feature(out_layer.GetLayerDefn())
        out_feature.SetGeometry(feature.GetGeometryRef().Clone())
        height = feature.GetField('height_m')
        label = f'{height:.1f}m'
        out_feature.SetField('label', label)
        style = f'LABEL(f:"Arial Bold",s:8pt,t:"{label}",c:#000000,dx:6,dy:3,bo:#FFFFFF,hc:#FFFFFF,ho:2.5)'
        out_feature.SetField('OGR_STYLE', style)
        out_layer.CreateFeature(out_feature)
    
    points_ds = None
    out_ds = None

def create_line_labels(input_dir):
    """Create line labels layer"""
    lines_shp = os.path.join(input_dir, 'lines.shp')
    labels_shp = os.path.join(input_dir, 'line_labels.shp')
    
    driver = ogr.GetDriverByName('ESRI Shapefile')
    if os.path.exists(labels_shp):
        driver.DeleteDataSource(labels_shp)
    
    out_ds = driver.CreateDataSource(labels_shp)
    out_layer = out_ds.CreateLayer('line_labels', geom_type=ogr.wkbPoint)
    
    label_field = ogr.FieldDefn('label', ogr.OFTString)
    style_field = ogr.FieldDefn('OGR_STYLE', ogr.OFTString)
    out_layer.CreateField(label_field)
    out_layer.CreateField(style_field)
    
    lines_ds = ogr.Open(lines_shp)
    lines_layer = lines_ds.GetLayer()
    
    for feature in lines_layer:
        geom = feature.GetGeometryRef()
        distance = feature.GetField('distance')
        points = geom.GetPoints()
        
        if len(points) >= 2:
            start_point = points[0]
            end_point = points[-1]
            
            mid_x = (start_point[0] + end_point[0]) / 2
            mid_y = (start_point[1] + end_point[1]) / 2
            
            dx = end_point[0] - start_point[0]
            dy = end_point[1] - start_point[1]
            angle = math.degrees(math.atan2(dy, dx))
            
            if angle < -90 or angle > 90:
                angle += 180
            
            point = ogr.Geometry(ogr.wkbPoint)
            point.AddPoint(mid_x, mid_y)
            
            out_feature = ogr.Feature(out_layer.GetLayerDefn())
            out_feature.SetGeometry(point)
            label = f'{distance:.1f}m'
            out_feature.SetField('label', label)
            style = f'LABEL(f:"Arial",s:10pt,t:"{label}",c:#000000,a:{angle:.1f})'
            out_feature.SetField('OGR_STYLE', style)
            out_layer.CreateFeature(out_feature)
    
    lines_ds = None
    out_ds = None

def calculate_page_dimensions(input_tiff):
    """Calculate dimensions for the output page based on input TIFF"""
    ds = gdal.Open(input_tiff)
    original_width = ds.RasterXSize
    original_height = ds.RasterYSize
    gt = ds.GetGeoTransform()
    proj = ds.GetProjection()
    ds = None
    
    # Make the page width 2x the original
    page_width = original_width * 2
    page_height = original_height
    
    # Calculate offset to place the content on the right half
    x_offset = int(original_width * 0.8)  # Position at 80% of original width
    y_offset = 0  # Keep vertical position the same
    
    return {
        'page_width': page_width,
        'page_height': page_height,
        'x_offset': x_offset,
        'y_offset': y_offset,
        'original_width': original_width,
        'original_height': original_height,
        'geotransform': gt,
        'projection': proj
    }

def create_georef_pdf(input_tiff, input_dir, output_pdf, logo_path=None, logo_size=(20, 20)):
    """Create georeferenced PDF with all layers and logo on a larger page"""
    try:
        # Calculate dimensions
        dimensions = calculate_page_dimensions(input_tiff)
        
        # Modify vector styles (keep existing vector layers)
        modify_segments_style(input_dir)
        modify_lines_style(input_dir)
        modify_points_style(input_dir)
        create_well_space_points(input_dir)
        create_point_labels(input_dir)
        create_line_labels(input_dir)
        
        # Create temporary larger TIFF
        temp_larger = os.path.join(input_dir, 'temp_larger.tif')
        if os.path.exists(temp_larger):
            os.remove(temp_larger)
            
        # Open input TIFF
        src_ds = gdal.Open(input_tiff)
        gt = src_ds.GetGeoTransform()
        
        # Create new geotransform for the larger image
        # Shift the origin to place content on the right
        new_gt = list(gt)
        new_gt[0] = gt[0] + (dimensions['x_offset'] * gt[1])  # Shift X origin
        
        # Create larger TIFF
        driver = gdal.GetDriverByName('GTiff')
        larger_ds = driver.Create(temp_larger,
                                dimensions['page_width'],
                                dimensions['page_height'],
                                src_ds.RasterCount,
                                src_ds.GetRasterBand(1).DataType,
                                options=['COMPRESS=LZW'])
        
        # Set spatial reference
        larger_ds.SetProjection(src_ds.GetProjection())
        larger_ds.SetGeoTransform(tuple(new_gt))
        
        # Fill with white
        for i in range(1, larger_ds.RasterCount + 1):
            band = larger_ds.GetRasterBand(i)
            band.Fill(255)
        
        # Copy original data to the right position
        for i in range(1, src_ds.RasterCount + 1):
            src_band = src_ds.GetRasterBand(i)
            dst_band = larger_ds.GetRasterBand(i)
            data = src_band.ReadAsArray()
            dst_band.WriteArray(data, dimensions['x_offset'], dimensions['y_offset'])
        
        larger_ds.FlushCache()
        src_ds = None
        larger_ds = None
        
        # Create PDF
        pdf_options = [
            f"OGR_DATASOURCE={input_dir}",
            "OGR_DISPLAY_FIELD=class",
            "OGR_DISPLAY_LAYER=segments,lines,points,well_space,point_labels,line_labels",
            "LAYER_NAME=Ortho Image",
            "EXTRA_LAYER_NAME=Vector Overlay",
            "PDF_LAYER_ORDER=ON",
            "OGR_PDF_WRITE_INFO=ON",
            "DPI=300",
            "GEO_ENCODING=ISO32000",
            "MARGIN=0",
            "COMPRESS=JPEG",
            "JPEG_QUALITY=90"
        ]
        
        translate_options = gdal.TranslateOptions(
            format="PDF",
            creationOptions=pdf_options
        )
        
        print("Creating final PDF...")
        result = gdal.Translate(output_pdf, temp_larger, options=translate_options)
        
        if result is None:
            raise ValueError("PDF creation failed")
        
        result = None
        
        # Clean up
        if os.path.exists(temp_larger):
            os.remove(temp_larger)
            
        print(f"Successfully created PDF: {output_pdf}")
        
    except Exception as e:
        print(f"Error creating PDF: {str(e)}")
        raise

def main():
    input_tiff = r"C:\Users\User\Downloads\1627_utm_checked\1627_utm_checked\1627_utm\P2_35A_imagesRGB_orthomosaic.tif"
    input_directory = r"C:\Users\User\Downloads\1627_utm_checked\1627_utm_checked\Results\vectors"
    output_pdf = "complete_styled_georef.pdf"
    logo_path = r"C:\Users\User\Downloads\pole.png"
    
    logo_size = (140, 140)
    
    # Ensure input files exist
    if not os.path.exists(input_tiff):
        raise FileNotFoundError(f"Input TIFF not found: {input_tiff}")
    if not os.path.exists(input_directory):
        raise FileNotFoundError(f"Input directory not found: {input_directory}")
    
    create_georef_pdf(input_tiff, input_directory, output_pdf, 
                     logo_path=logo_path, 
                     logo_size=logo_size)

if __name__ == "__main__":
    gdal.UseExceptions()
    main()


