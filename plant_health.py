# Now in this I have to look for plant height, and plant age as well like if the plant of this age then it is of this height and canopy 

import os
from utils_plant import *

class PlantHealth:
    def __init__(self, input_folder, output_folder, dem_folder,  reference_dict):
        self.image_folder = input_folder
        self.output_folder = output_folder
        self.dem_folder = dem_folder
        self.utils_obj = UtilsHealth(reference_dict)
    
    
    def processs_image(self):
        img_files = os.listdir(self.image_folder)
        valid_extensions = ['.png', '.jpg', '.tiff', '.tif']
        
        for img in img_files:
            if any(img.lower().endswith(ext) for ext in valid_extensions):
                img_path = os.path.join(self.image_folder, img)
                parts = img.split('_')
                parts[-1] = "dem_dem_norm_utm.tif"
                dem_name = "_".join(parts)
                dem_path = os.path.join(self.dem_folder, dem_name)
                json_path = os.path.join(
                    self.image_folder,
                    os.path.splitext(img)[0] + ".json"
                )
                output_geojson =  os.path.join(
                    self.output_folder,
                    os.path.splitext(img)[0] + ".geojson"
                )
                
                self.utils_obj.tree_health_calculator(img_path, dem_path, json_path, output_geojson)
                

if __name__ == "__main__":
    input_folder= r"C:\Users\User\Downloads\1628_results_Checked\1628_results_Checked\test\data_utm\for-semi"
    dem_folder = r"C:\Users\User\Downloads\1628_results_Checked\1628_results_Checked\test\Dem_utm"
    output_folder = r"C:\Users\User\Downloads\1628_results_Checked\1628_results_Checked\test_result"
    os.makedirs(output_folder, exist_ok=True)
    reference_dict = {
    "tree": [
        {"age": 5, "height": 3.5, "canopy_area": 3.1},
        {"age": 10, "height": 8, "canopy_area": 12.1},
        {"age": 20, "height": 15, "canopy_area": 28.3},
        {"age": 30, "height": 22, "canopy_area": 44.3},
        {"age": 40, "height": 30, "canopy_area": 70.9},
    ]
}

    
    temp_obj = PlantHealth(input_folder, output_folder, dem_folder, reference_dict)
    temp_obj.processs_image()