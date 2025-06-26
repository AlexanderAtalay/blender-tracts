# Blender Tracts
### Create Stunning Tractography Visualizations in Blender with Ease

![alt text](https://github.com/AlexanderAtalay/blender-tracts/blob/main/resources/blender_tracts_banner.jpg "Superior-Inferior Streamlines Isolated and Visualized with Blender Tracts")

Verson 1.0.0

Blender Tracts is a lightweight Blender add-on that allows you to visualize tractography data as mesh streamlines with endless customization. Streamlines can either be loaded in and sampled directly from a .tck file or from a .txt file where every line is a list of lists containing the three-dimensional coordinates of streamline control points. This allows pre-indexed sampling, which will be useful when Blender Tracts allows for scalar support in the near future.

Blender Tracts assigns each streamline to a set of geometry nodes that allows them to behave like a class, allowing for full customizability of the shape, smoothing, radius, etc of each individual tract. By default, the streamlines are colored as RGB based on the orientation of their tangent (green: anterior-posterior, red: medial-lateral, blue: superior-inferior).

## Installation

To install Blender Tracts, simply download this repository, go to Edit->Preferences->Add-ons->Install from Disk, and select `blender_tracts.py`. Blender Tracts will be accessible from the 'Tools' section on the right-hand side of the 3D Viewer pane. The geometry and shader nodes can be modified to easily apply effects to every streamline for visualization purposes.

## Contributors

- Alexander Atalay ([asatalay@stanford.edu](mailto:asatalay@mstanford.edu))