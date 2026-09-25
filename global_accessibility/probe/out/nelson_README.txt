***Travel times to cities and ports in the year 2015***
Authors:Nelson, Andy

Contact information:
a.nelson@utwente.nl
Full Professor, Department of Natural Resources
Faculty of Geo-Information Science and Earth Observation (ITC), University of Twente, The Netherlands
https://orcid.org/0000-0002-7249-3778

***General Introduction***

The dataset is a suite of global travel-time accessibility indicators for the year 2015, at 30 arc seconds (approximately one kilometre) spatial resolution for the entire globe. The indicators show an estimated (and validated), land-based travel time to the nearest city and nearest port for a range of city and port sizes.
The datasets are in GeoTIFF format and are suitable for use in Geographic Information Systems and statistical packages for mapping access to cities and ports and for spatial and statistical analysis of the inequalities in access by different segments of the population.
These maps represent a unique global representation of physical access to essential services offered by cities and ports.

file naming convention
travel_time_to_cities_x.tif (x has values from 1 to 12) 
The value of each pixel is the estimated travel time in minutes to the nearest urban area in 2015. There are 12 data 
layers based on different sets of urban areas, defined by their population in year 2015. 
x in filename		Population minimum (>=)		Population maximum (<) 
1 			5,000,000			50,000,000
2 			1,000,000			5,000,000
3 			500,000				1,000,000
4 			200,000				500,000
5 			100,000				200,000
6 			50,000				100,000
7 			20,000				50,000
8 			10,000				20,000
9 			5,000				10,000
10 			20,000				110,000,000
11 			50,000				50,000,000
12 			5,000				110,000,000

travel_time_to_ports_x (x ranges from 1 to 5) 
The value of each pixel is the estimated travel time to the nearest port in 2015. There are 5 data layers based on 
different port sizes. 
x in file name	Port size	Number of ports 
1 		Large 		160
2 		Medium 		361
3 		Small 		990
4 		Very small 	2,153
5 		Any 		3,77

***Data specific information***

Data format 
Raster Dataset, GeoTIFF, LZW compression

Unit 
Minutes

Data type 
Byte (16 bit Unsigned Integer)

No data value 
65535

Flags 
None

Spatial resolution 
30 arc seconds

Spatial extent 
Upper left -180, 85
Lower left -180, -60
Upper right 180, 85
Lower right 180, -60

Spatial Reference System (SRS) 
EPSG:4326 - WGS84 - Geographic Coordinate System (lat/long)

Temporal resolution 
2015

Temporal extent 
Updates may follow for future years, but these are dependent on the availability of updated inputs on travel times 
and city locations and populations.

***Methodology***

Travel time to the nearest port was estimated using an accumulated cost function (accCost) in the gdistance R 
package (van Etten, 2018). This function requires two input datasets: (i) a set of locations to estimate travel time to 
and (ii) a transition matrix that represents the cost or time to travel across a surface. 
Marine ports were extracted from the 26th edition of the World Port Index (NGA, 2017) which contains the location 
and physical characteristics of approximately 3,700 major ports and terminals. Ports are represented as single points 
The transition matrix was based on the friction surface (https://map.ox.ac.uk/researchproject/accessibility_to_cities) from the 2015 global accessibility map (Weiss et al, 2018).


The R code used to generate the 5 travel time maps is included in the report “A suite of global accessibility indicators 
for sustainable rural development” (Nelson, 2019) that can be downloaded with these data layers.

***Validation***

The underlying friction surface was validated by comparing travel times between 47,893 pairs of locations against journey times from a Google API. Our estimated journey times were generally shorter than those from the Google API. 
Across the tiles, the median journey time from our estimates was 88 minutes within an interquartile range of 48 to 143 minutes while the median journey time estimated by the Google API was 106 minutes within an interquartile range of 61 to 167 minutes. 
Across all tiles, the differences were skewed to the left and our travel time estimates were shorter than those reported by the Google API in 72% of the tiles. The median difference was −13.7 minutes within an interquartile range of −35.5 to 2.0 minutes while the absolute difference was 30 minutes or less for 60% of the tiles and 60 minutes or less for 80% of the tiles. 
The median percentage difference was −16.9% within an interquartile range of −30.6% to 2.7% while the absolute percentage difference was 20% or less in 43% of the tiles and 40% or less in 80% of the tiles.

This process and results are included in the validation zip file.

***Usage notes***

The accessibility layers can be visualised and analysed in many Geographic Information Systems or remote sensing software such as QGIS, GRASS, ENVI, ERDAS or ArcMap, and also by statistical and modelling packages such as R or MATLAB. They can also be used in cloud-based tools for geospatial analysis such as Google Earth Engine.
The nine layers represent travel times to human settlements of different population ranges. Two or more layers can be combined into one layer by recording the minimum pixel value across the layers. For example, a map of travel time to the nearest settlement of 5,000 to 50,000 people could be generated by taking the minimum of the three layers that represent the travel time to settlements with populations between 5,000 and 10,000, 10,000 and 20,000 and, 20,000 and 50,000 people.
The accessibility layers also permit user-defined hierarchies that go beyond computing the minimum pixel value across layers. A user-defined complete hierarchy can be generated when the union of all categories adds up to the global population, and the intersection of any two categories is empty. Everything else is up to the user in terms of logical consistency with the problem at hand.
The accessibility layers are relative measures of the ease of access from a given location to the nearest target. While the validation demonstrates that they do correspond to typical journey times, they cannot be taken to represent actual travel times. Errors in the friction surface will be accumulated as part of the accumulative cost function and it is likely that locations that are further away from targets will have greater a divergence from a plausible travel time than those that are closer to the targets. Care should be taken when referring to travel time to the larger cities when the locations of interest are extremely remote, although they will still be plausible representations of relative accessibility. Furthermore, a key assumption of the model is that all journeys will use the fastest mode of transport and take the shortest path.

***Access information***

Licence CC BY 4.0

***Reuse data***
I you want to start using this dataset in an executable environment, use the following link to open a jupyter notebook in which data is ready to use.
[![Binder](https://mybinder.org/badge_logo.svg)](https://mybinder.org/v2/gh/MasoomeShariat/Open_DataPub_Andy_Dataset/HEAD) 

***References***
 
NGA. World Port Index 26th edition. 
(2017). https://msi.nga.mil/NGAPortal/MSI.portal?_nfpb=true&_pageLabel=msi_portal_page_62&pubCode=0015

Nelson, A. A suite of global accessibility indicators for sustainable rural development. (2019) A report prepared for 
the CGIAR Consortium for Spatial Information 

Weiss, D. J. et al. A global map of travel time to cities to assess inequalities in accessibility in 2015. Nature (2018). 
doi:10.1038/nature25181

van Etten, J. gdistance: Distances and Routes on Geographical Grids. (2018). https://cran.rproject.org/package=gdistanc
