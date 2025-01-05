import json
import math
from collections import defaultdict
from shapely.geometry import Polygon, Point
import numpy as np
from geopy.distance import geodesic

class TreeGraph:
    def __init__(self, well_space_dist):
        self.nodes = {}
        self.edges = defaultdict(list)
        self.well_space_dist = well_space_dist  # Distance in meters

    def add_node(self, tree_id, coords, height):
        # coords should be (lon, lat) in WGS84
        self.nodes[tree_id] = {
            'coords': coords,
            'height': height
        }

    def add_edge(self, id1, id2, distance):
        self.edges[id1].append((id2, distance))
        self.edges[id2].append((id1, distance))

    def get_neighbors(self, node_id):
        return self.edges[node_id]

    def is_well_spaced(self, tree_id, removed_trees):
        if tree_id in removed_trees:
            return False
        return all((neighbor in removed_trees or dist >= self.well_space_dist)
                   for neighbor, dist in self.edges[tree_id])

    def count_well_spaced(self, removed_trees):
        return sum(1 for tree_id in self.nodes if self.is_well_spaced(tree_id, removed_trees))

class TreeOptimizer:
    def __init__(self, buffer_dist=3, well_space_dist=1):
        # buffer_dist and well_space_dist should be in meters
        self.buffer_dist = buffer_dist
        self.well_space_dist = well_space_dist
    
    def geographic_distance(self, coord1, coord2):
        """Calculate distance between two geographic coordinates in meters"""
        # coord1 and coord2 should be (lon, lat)
        return geodesic((coord1[1], coord1[0]), (coord2[1], coord2[0])).meters

    def load_and_build_graph(self):
        with open(self.file_path, 'r') as f:
            data = json.load(f)

        features = data['features']
        self.total_trees = len(features)

        # Add nodes using centroids
        for i, feature in enumerate(features):
            tree_id = f"tree_{i}"
            polygon_coords = feature['geometry']['coordinates'][0]
            polygon = Polygon(polygon_coords)
            centroid = polygon.centroid
            coords = (centroid.x, centroid.y)  # (lon, lat)
            height = feature['properties'].get('height_meters', 0)
            self.graph.add_node(tree_id, coords, height)

        # Add edges between nodes if distance <= buffer_dist
        for i, feature1 in enumerate(features):
            for j in range(i + 1, len(features)):
                tree_id1 = f"tree_{i}"
                tree_id2 = f"tree_{j}"

                coords1 = self.graph.nodes[tree_id1]['coords']
                coords2 = self.graph.nodes[tree_id2]['coords']

                distance = self.geographic_distance(coords1, coords2)
                if distance <= self.buffer_dist:
                    self.graph.add_edge(tree_id1, tree_id2, distance)

    def find_conflicting_pairs(self, removed_trees):
        conflicts = []
        processed = set()

        for tree_id in self.graph.nodes:
            if tree_id in removed_trees or tree_id in processed:
                continue
            for neighbor_id, dist in self.graph.edges[tree_id]:
                if neighbor_id not in removed_trees and neighbor_id not in processed and dist < self.well_space_dist:
                    conflicts.append((tree_id, neighbor_id))
                    processed.add(neighbor_id)
            processed.add(tree_id)

        return conflicts

    def evaluate_removal(self, tree_id, removed_trees):
        before_count = self.graph.count_well_spaced(removed_trees)
        temp_removed = removed_trees | {tree_id}
        after_count = self.graph.count_well_spaced(temp_removed)
        return after_count - before_count

    def optimize_spacing(self):
        removed_trees = set()
        iteration = 0
        max_iterations = len(self.graph.nodes) * 2

        while iteration < max_iterations:
            conflicts = self.find_conflicting_pairs(removed_trees)
            if not conflicts:
                break

            improved = False
            for tree1, tree2 in conflicts:
                if tree1 in removed_trees or tree2 in removed_trees:
                    continue

                gain1 = self.evaluate_removal(tree1, removed_trees)
                gain2 = self.evaluate_removal(tree2, removed_trees)

                if gain1 > 0 or gain2 > 0:
                    if gain1 > gain2:
                        removed_trees.add(tree1)
                    elif gain2 > gain1:
                        removed_trees.add(tree2)
                    else:
                        height1 = self.graph.nodes[tree1]['height']
                        height2 = self.graph.nodes[tree2]['height']
                        removed_trees.add(tree1 if height1 < height2 else tree2)
                    improved = True

            if not improved:
                break
            iteration += 1

        return removed_trees

    def well_space_calculator(self, input_path, output_path):
        self.graph = TreeGraph(self.well_space_dist)
        self.file_path = input_path
        self.total_trees = 0
        self.load_and_build_graph()
        removed_trees = self.optimize_spacing()

        well_spaced_trees = [
            tree_id for tree_id in self.graph.nodes
            if tree_id not in removed_trees and self.graph.is_well_spaced(tree_id, removed_trees)
        ]
        
        new_features = []
        with open(self.file_path, 'r') as f:
            data = json.load(f)

        # Add CRS information to ensure WGS84 is specified
        new_geojson = {
            "type": "FeatureCollection",
            "crs": {
                "type": "name",
                "properties": {
                    "name": "urn:ogc:def:crs:EPSG::4326"
                }
            },
            "features": []
        }

        for i, feature in enumerate(data['features']):
            tree_id = f"tree_{i}"
            height = feature["properties"].get("height_meters", 0)

            polygon = Polygon(feature['geometry']['coordinates'][0])
            centroid = polygon.centroid
            
            new_feature = {
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [centroid.x, centroid.y]  # [lon, lat]
                },
                "properties": {
                    "class": '1' if tree_id in well_spaced_trees else '0',
                    "height_meters": height
                }
            }
            new_features.append(new_feature)

        new_geojson["features"] = new_features

        with open(output_path, 'w') as f:
            json.dump(new_geojson, f)

        heights = [f["properties"]["height_meters"] for f in new_features if f["properties"]["class"] == '1']
        return len(well_spaced_trees), np.average(heights) if heights else 0



# if __name__ == "__main__":
#     file_path = r"C:\Users\User\Downloads\1628_results_Checked\1628_results_Checked\test\Health_Results\P2_19B_imagesRGB_orthomosaic_result.geojson"
#     output_path = r"C:\Users\User\Downloads\1628_results_Checked\1628_results_Checked\test\Health_Results\P2_19B_imagesRGB_orthomosaic_result.geojson"
#     optimizer = TreeOptimizer()
#     result, he = optimizer.well_space_calculator(file_path, output_path)
#     print(result, he)
    
