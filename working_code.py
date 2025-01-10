from osgeo import gdal, ogr, osr
import os
import math

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
    
    # Create new shapefile for well-space points
    driver = ogr.GetDriverByName('ESRI Shapefile')
    if os.path.exists(well_space_shp):
        driver.DeleteDataSource(well_space_shp)
    
    out_ds = driver.CreateDataSource(well_space_shp)
    out_layer = out_ds.CreateLayer('well_space', geom_type=ogr.wkbPoint)
    
    # Add fields
    class_field = ogr.FieldDefn('class', ogr.OFTString)
    style_field = ogr.FieldDefn('OGR_STYLE', ogr.OFTString)
    out_layer.CreateField(class_field)
    out_layer.CreateField(style_field)
    
    # Copy class 1 points
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
            
            # Calculate midpoint and angle
            mid_x = (start_point[0] + end_point[0]) / 2
            mid_y = (start_point[1] + end_point[1]) / 2
            
            dx = end_point[0] - start_point[0]
            dy = end_point[1] - start_point[1]
            angle = math.degrees(math.atan2(dy, dx))
            
            if angle < -90 or angle > 90:
                angle += 180
            
            # Create label point
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

def create_georef_pdf(input_tiff, input_dir, output_pdf):
    """Create georeferenced PDF with all layers"""
    # Modify/create all styled layers
    modify_segments_style(input_dir)
    modify_lines_style(input_dir)
    modify_points_style(input_dir)
    create_well_space_points(input_dir)
    create_point_labels(input_dir)
    create_line_labels(input_dir)
    
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
            "PDF_LAYER_ORDER=ON",
            "OGR_PDF_WRITE_INFO=ON",
            "DPI=300",
            "GEO_ENCODING=ISO32000",
            "MARGIN=0",
            "EXTRA_STREAM=OPACITY:100"
        ]
    )
    
    # Create PDF with all layers
    gdal.Translate(output_pdf, input_tiff, options=translate_options)

def main():
    input_tiff = r"C:\Users\User\Downloads\1627_utm_checked\1627_utm_checked\1627_utm\P2_35A_imagesRGB_orthomosaic.tif"
    input_directory = r"C:\Users\User\Downloads\1627_utm_checked\1627_utm_checked\Results\vectors"
    output_pdf = "complete_styled_georef.pdf"
    
    create_georef_pdf(input_tiff, input_directory, output_pdf)

if __name__ == "__main__":
    main()