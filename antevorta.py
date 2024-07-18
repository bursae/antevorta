import pandas as pd
import numpy as np
import geopandas as gpd
from shapely.geometry import Point
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
import matplotlib.pyplot as plt

# Load data
data = pd.read_csv('crime_data.csv')

# Preprocess data
data['date'] = pd.to_datetime(data['date'])
data['hour'] = data['date'].dt.hour
data['day_of_week'] = data['date'].dt.dayofweek
data['month'] = data['date'].dt.month

# Drop rows with missing values
data.dropna(inplace=True)

# Create a GeoDataFrame for crime data
geometry = [Point(xy) for xy in zip(data['longitude'], data['latitude'])]
gdf = gpd.GeoDataFrame(data, geometry=geometry)

# Load geospatial factor data, e.g., police stations
police_stations = gpd.read_file('police_stations.shp')
police_stations = police_stations.to_crs(gdf.crs)

# Calculate distance to nearest police station
gdf['nearest_station_distance'] = gdf.geometry.apply(
    lambda x: police_stations.distance(x).min()
)

# Load polygon data for demographics
demographics = gpd.read_file('demographics.shp')  # Assuming a shapefile
demographics = demographics.to_crs(gdf.crs)

# Spatial join to get demographic data
gdf = gpd.sjoin(gdf, demographics, how='left', op='intersects')

# Encode type_of_crime as numerical values
data['type_of_crime'] = data['type_of_crime'].astype('category').cat.codes

# Define features and target variable
features = ['hour', 'day_of_week', 'month', 'longitude', 'latitude', 'nearest_station_distance'] + list(demographics.columns.drop('geometry'))
X = gdf[features]
y = data['type_of_crime']

# Split data into training and testing sets
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.3, random_state=42)

# Train a Random Forest model
model = RandomForestClassifier(n_estimators=100, random_state=42)
model.fit(X_train, y_train)

# Evaluate the model
accuracy = model.score(X_test, y_test)
print(f'Model Accuracy: {accuracy:.2f}')

# Predict crime types on the test set
y_pred = model.predict(X_test)

# Add predictions to the GeoDataFrame
X_test['predicted_crime'] = y_pred

# Visualize predicted crime hotspots
gdf_test = gpd.GeoDataFrame(X_test, geometry=[Point(xy) for xy in zip(X_test['longitude'], X_test['latitude'])])
fig, ax = plt.subplots(1, 1, figsize=(10, 10))
gdf_test.plot(column='predicted_crime', ax=ax, legend=True, cmap='OrRd')

# Customize the plot
ax.set_title('Predicted Crime Hotspots')
plt.show()
