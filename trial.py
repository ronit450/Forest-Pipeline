from osgeo import gdal, ogr, osr
import os
import math
import numpy as np
from PIL import Image



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

def create_georeferenced_logo(input_tiff, logo_path, output_dir, position=(50, 50), logo_size=(300, 300)):
    """Create a georeferenced logo overlay with custom positioning
    
    Args:
        input_tiff: Input TIFF file path
        logo_path: Path to the logo/TIFF to overlay
        output_dir: Output directory
        position: (x, y) position from top-left in pixels
        logo_size: (width, height) size of the overlay
    """
    # Get input TIFF information
    ds = gdal.Open(input_tiff)
    gt = ds.GetGeoTransform()
    proj = ds.GetProjection()
    
    # Use provided position instead of calculating from edges
    pixel_x = position[0]  # X position from left
    pixel_y = position[1]  # Y position from top
    
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

def create_georef_pdf(input_tiff, input_dir, output_pdf, logo_path=None, logo_size=(300, 300), logo_position=(50, 50)):
    """Create georeferenced PDF with all layers and positioned overlay"""
    # Modify/create all styled layers
    modify_segments_style(input_dir)
    modify_lines_style(input_dir)
    modify_points_style(input_dir)
    create_well_space_points(input_dir)
    create_point_labels(input_dir)
    create_line_labels(input_dir)
    
    # Process logo if provided
    temp_files = []
    if logo_path and os.path.exists(logo_path):
        # Create georeferenced logo overlay with custom position
        logo_tiff = create_georeferenced_logo(
            input_tiff, 
            logo_path, 
            input_dir, 
            position=logo_position,
            logo_size=logo_size
        )
        temp_files.append(logo_tiff)
        
        # Merge logo with input TIFF
        temp_merged = os.path.join(input_dir, 'temp_merged.tif')
        temp_files.append(temp_merged)
        
        gdal.Warp(
            temp_merged, 
            [logo_tiff, input_tiff],  # Note: logo is the first layer
            format='GTiff',
            options=[
                'COMPRESS=LZW',
                'ALPHA=YES'
            ]
        )
        
        input_tiff = temp_merged
    
    # Register PDF driver and set up options
    gdal.GetDriverByName('PDF').Register()
    
    translate_options = gdal.TranslateOptions(
        format="PDF",
        creationOptions=[
            f"OGR_DATASOURCE={input_dir}",
            "OGR_DISPLAY_FIELD=class",
            "OGR_DISPLAY_LAYER=segments,lines,points,well_space,point_labels,line_labels",
            "LAYER_NAME=Ortho Image",
            "EXTRA_LAYER_NAME=Vector Overlay",
            "PDF_LAYER_ORDER=OFF",  # Maintain layer hierarchy
            "OGR_PDF_WRITE_INFO=ON",
            "DPI=300",
            "GEO_ENCODING=ISO32000",
            "MARGIN=0",
            "EXTRA_STREAM=OPACITY:100"
        ]
    )
    
    gdal.Translate(output_pdf, input_tiff, options=translate_options)
    
    # Clean up temporary files
    for temp_file in temp_files:
        if os.path.exists(temp_file):
            os.remove(temp_file)

def main():
    input_tiff = r"C:\Users\User\Downloads\1627_utm_checked\1627_utm_checked\1627_utm\P2_35A_imagesRGB_orthomosaic.tif"
    input_directory = r"C:\Users\User\Downloads\1627_utm_checked\1627_utm_checked\Results\vectors"
    output_pdf = "complete_styled_georef.pdf"
    logo_path = r"C:\Users\User\Downloads\1627jpgs\jpgs\silviculture-report-A-35.jpg"
    
    # Adjust these values to position your TIFF where you want it
    logo_size = (3500, 3500)  # Size of the TIFF overlay
    logo_position = (-1700, -1200)  # Position from top-left corner
    
    create_georef_pdf(
        input_tiff, 
        input_directory, 
        output_pdf, 
        logo_path=logo_path,
        logo_size=logo_size,
        logo_position=logo_position
    )

if __name__ == "__main__":
    main()