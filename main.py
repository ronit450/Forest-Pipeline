import os
from utils_plant import *
from well_space import *
from overall_utils import * 
import shutil
import warnings
from tqdm import tqdm
from multiprocessing import Pool, cpu_count
warnings.filterwarnings('ignore')

class Tree_all:
    def __init__(self, input_path, dem_folder, csv_path, reference_dict):
        self.image_folder = input_path
        self.dem_folder = dem_folder
        self.reference_dict = reference_dict
        self.csv_path = csv_path
        
        self.plantHealth_obj = UtilsHealth(reference_dict)
        self.wellSpace_obj = TreeOptimizer()
        self.overall_utils = TreeUtils()
        self.plot_vector = TreeVectorViz()
        
        result_folder= self.folder_maker(os.path.join(os.path.dirname(input_path), 'Results'))
        
        self.health_folder = self.folder_maker(os.path.join(result_folder, 'Health_Results'))
        self.wellspace_folder = self.folder_maker(os.path.join(result_folder, 'WellSpace_Geojsons'))
        self.line_folder = self.folder_maker(os.path.join(result_folder, 'Line_Geojsons'))
        self.visulization_folder = self.folder_maker(os.path.join(result_folder, 'Visulizations'))
        self.output_csv_path = os.path.join(os.path.join(result_folder, "summary.csv"))
        
    def folder_maker(self, path):
        if os.path.exists(path):
            shutil.rmtree(path)
        os.makedirs(path, exist_ok=True)
        return path
    
    def csv_maker(self, result, output_csv_path):
        df = pd.DataFrame(result)
        df.to_csv(output_csv_path, index=False)
        print(f"CSV saved successfully to {output_csv_path}")

    def process_single_image(self, img):
        valid_extensions = ['.png', '.jpg', '.tiff', '.tif']
        if not any(img.lower().endswith(ext) for ext in valid_extensions):
            return None

        img_path = os.path.join(self.image_folder, img)
        parts = img.split('_')
        parts[-1] = "dem_dem_norm_utm.tif"
        dem_name = "_".join(parts)
        dem_path = os.path.join(self.dem_folder, dem_name)
        json_path = os.path.join(self.image_folder, os.path.splitext(img)[0] + ".json")
        health_geojson = os.path.join(self.health_folder, os.path.splitext(img)[0] + ".geojson")
        wellSpace_geojson = os.path.join(self.wellspace_folder, os.path.splitext(img)[0] + ".geojson")
        line_geojson = os.path.join(self.line_folder, os.path.splitext(img)[0] + ".geojson")
        visualization_output = os.path.join(self.visulization_folder, img)

        totalArea_conifer, avgHeight, small, medium, large = self.plantHealth_obj.tree_health_calculator(
            img_path, dem_path, json_path, health_geojson)
        totalImageArea = self.overall_utils.image_area(img_path)
        wellspace_count, well_space_avg_height = self.wellSpace_obj.well_space_calculator(
            health_geojson, wellSpace_geojson)
    
        self.overall_utils.create_segment_connections(health_geojson, line_geojson)
        self.plot_vector.plot_vector_visualization(
            
            img_path, line_geojson,  wellSpace_geojson,health_geojson,  visualization_output)
        scout_area = self.overall_utils.scoout_area()
        total_confiffers = self.overall_utils.total_coniffer(json_path)
        plot_number, stratum = self.overall_utils.extract_plot_and_stratum(img_path)
        csv_data = self.overall_utils.data_csv(self.csv_path, plot_number, stratum)
        temp = f"silviculture/zanzibar/1627/{img}"
        s3_url = self.overall_utils.upload_to_s3(visualization_output, 'datastore-farmevo', temp)

        return {
            "company": csv_data.get("location"),
            "block": csv_data.get("block"),
            "stratum": stratum,
            "plot": plot_number,
            "scout_area": scout_area,
            "TreeType": csv_data.get("treeType"),
            "scan_date": csv_data.get("flightDate"),
            "avgTreeHeight": avgHeight,
            "avgTreeHeight_well_spaced": well_space_avg_height,
            "totalTrees": total_confiffers,
            "wellSpacedTrees": wellspace_count,
            "height_lt_1.5": small,
            "height_gte_1.5_lt_2.5": medium,
            "height_gte_2.5": large,
            "slashArea": csv_data.get("slashArea"),
            "crown_closureArea": totalArea_conifer,
            "crown_closureArea_Percent": (totalArea_conifer / totalImageArea) * 100, 
            "s3-URL": s3_url
        }

    def processs_image(self):
        img_files = os.listdir(self.image_folder)
        total_files = len([f for f in img_files if any(f.lower().endswith(ext) 
                        for ext in ['.png', '.jpg', '.tiff', '.tif'])])
        
        print(f"Processing {total_files} images with {cpu_count()} CPU cores")
        
        with Pool(processes=cpu_count()) as pool:
            results = list(tqdm(
                pool.imap(self.process_single_image, img_files),
                total=len(img_files),
                desc="Processing images"
            ))
        
        final_result = [r for r in results if r is not None]
        self.csv_maker(final_result, self.output_csv_path)

if __name__ == "__main__":
    input_path = r"C:\Users\User\Downloads\1627_utm_checked\1627_utm_checked\1627_utm"
    dem_path = r"C:\Users\User\Downloads\1627_utm_checked\1627_utm_checked\DEM_UTM"
    csv_path = r"C:\Users\User\Downloads\1627.csv"
    reference_dict = {
        "tree": [
            {"age": 5, "height": 3, "canopy_area": 3},
            {"age": 10, "height": 8, "canopy_area": 12},  
            {"age": 20, "height": 15, "canopy_area": 28},
            {"age": 30, "height": 22, "canopy_area": 44}, 
            {"age": 40, "height": 30, "canopy_area": 70},
        ]
    }
    temp_obj = Tree_all(input_path, dem_path, csv_path, reference_dict)
    temp_obj.processs_image()