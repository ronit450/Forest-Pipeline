import os
from utils import *


class heathDetector:
    def __init__(self, input_folder, output_folder, reference_dict):
        self.image_folder = input_folder
        self.output_folder = output_folder
        self.utils_obj = UtilsHealth(reference_dict)
    
    def processs_image(self):
        img_files = os.listdir(self.image_folder)
        valid_extensions = ['.png', '.jpg', '.tiff', '.tif']
        
        for img in img_files:
            if any(img.lower().endswith(ext) for ext in valid_extensions):
                img_path = os.path.join(self.image_folder, img)
                json_path = os.path.join(
                    self.image_folder,
                    os.path.splitext(img)[0] + ".json"
                )
                output_geojson =  os.path.join(
                    self.image_folder,
                    os.path.splitext(img)[0] + ".geojson"
                )
                self.utils_obj.crop_growth_Calculator(img_path, json_path, output_geojson)
                

if __name__ == "__main__":
    input_folder= r"C:\Users\User\Downloads\1628_results_Checked\1628_results_Checked\test"
    output_folder = r"C:\Users\User\Downloads\1628_results_Checked\1628_results_Checked\test_result"
    os.makedirs(output_folder, exist_ok=True)
    reference_dict = {"tree": 5}
    
    
    # crop health potatoe anything befoe 25 is different and after 25 is different
    
    temp_obj = heathDetector(input_folder, output_folder, reference_dict)
    temp_obj.processs_image()
    
                
        