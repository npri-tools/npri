# -*- coding: utf-8 -*-

## Dependencies and Imports
import pandas
import geopandas
import folium
import urllib.parse
import warnings
warnings.simplefilter(action='ignore', category=FutureWarning)

# NPRI
def get_npri_data(view, endpoint, params=None, sql=None, index=None): # Gets data using sql query or url
  # Get the filter and its values
  #print(view, endpoint, params, sql, index) # Debugging

  if endpoint == "sql":
    sql = urllib.parse.quote_plus(sql)
    url = 'https://hello-world-1-ixcan5eepa-uc.a.run.app/sql/'+sql
    report_url = None
  else:
    url = 'https://hello-world-1-ixcan5eepa-uc.a.run.app/api/data/'+view+'/'+params
    report_url = 'https://hello-world-1-ixcan5eepa-uc.a.run.app/api/report/'+view+'/'+params
  #print("getting data: ", url, report_url) # Debugging
  data = None
  try:
    data =pandas.read_json(url) #sqlize(view,params) # for testing on colab, just directly sqlize sqlize(view,params) / otherwise use url
    # Set index, if specified
    if index is not None:
      data.set_index(index, inplace=True)
  except:
    print("Error: We are unable to get the data.")
  return data, url, report_url

def parameterize(args):
  params = ""
  for k,v in args.items():
    if v is not None:
      params += k + "="
      for val in v:
        if (k == "substances") & (" " in str(val)):
          params += str(val).replace(' ', '%') + ","
        else:
          params += str(val).strip(" ") + ","
      params = params[:-1] # remove trailing ,
      params += ";"
  params = params[:-1] # remove trailing ;
  return params

class Charts():
  def show_bar_chart(self, attribute=None, title=None):
    """
    A basic chart of the data.

    Max 50 x-axis.
    """
    # Order data and make chart
    to_chart = self.working_data.sort_values(by=attribute, ascending=False)[0:50]
    ax = to_chart[[attribute]].plot(
      kind="bar", title=title, figsize=(20, 10), fontsize=16
    )
    ax.set_xlabel(self.index)
    ax.set_ylabel(attribute)

    return ax

class Maps():
  """
  A class that provides basic functions for classes with mappable data (Facilities, Places)
  """

  def style_map(self, scenario, geom_type, attribute=None, title=None):
    """
    A function to style map features.
    Scenarios: markers (w and w/o data), polygons (w and w/o data)
    title TBD
    """
    features = []

    if geom_type == "Point":
      if scenario == "Data":
        # Quantize data
        self.working_data['quantile'] = pandas.qcut(self.working_data[attribute], 4, labels=False, duplicates="drop")
        scale = {0: 8,1:12, 2: 16, 3: 24} # First quartile = size 8 circles, etc.
      # Temporarily project self.working_data for mapping purposes
      self.working_data.to_crs(4326, inplace=True)
      # Create a clickable marker for each facility
      for idx, row in self.working_data.iterrows():
        fill_color = "orange" # Default
        r = 12 # Default
        popup = "<h2>"+str(idx)+"</h2>" # Default
        if scenario == "Data":
          try:
            r = scale[row["quantile"]]
          except KeyError: # When NAN (no records for this pollutant, e.g.)
            r = 1
            fill_color = "black"
          popup = folium.Popup(popup+"<h3>"+attribute+"</h3>"+str(row[attribute]))

        features.append(
          folium.CircleMarker(
            location = [row["geometry"].y, row["geometry"].x],
            popup = popup,
            radius = r,
            color = "black",
            weight = .2,
            fill_color = fill_color,
            fill_opacity= .4
          )
        )
      self.working_data.to_crs(3347, inplace=True)

    elif (geom_type == "Polygon") or (geom_type == "MultiPolygon"):
      styles = {"fillColor": "blue", "fillOpacity": .2, "lineOpacity": .2, "weight": .2, "color": "black"} # Defaults
      tooltip_fields=[self.index] # Default

      if scenario == "Data":
        scale = {0: "yellow", 1:"orange", 2: "red", 3: "brown"} # First quartile = size 8 circles, etc.
        self.working_data['quantile'] = pandas.qcut(self.working_data[attribute], 4, labels=False, duplicates="drop")
        tooltip_fields.append(attribute)

      def choropleth(feature):
        this_style = styles
        if scenario == "Data":
          try:
            fill = scale[feature["properties"]["quantile"]]
          except KeyError:
            fill = "white" # None / No Value
          this_style["fillColor"] = fill
          this_style["fillOpacity"] = 0.7
        else:
          this_style = styles
        return this_style

      # Temporarily reset index for matching and tooltipping
      self.working_data.reset_index(inplace=True)
      tooltip = folium.GeoJsonTooltip(
        fields = tooltip_fields,
        #aliases=["State:", "2015 Median Income(USD):", "Median % Change:"],
        localize=True,
        sticky=False,
        labels=True,
        style="""
            background-color: #F0EFEF;
            border: 2px solid black;
            border-radius: 3px;
            box-shadow: 3px;
        """,
        max_width=800,
      ) # Add tooltip for identifying features

      layer = folium.GeoJson(
        self.working_data,
        tooltip = tooltip,
        style_function = lambda feature: choropleth(feature)
      )

      features.append(layer)

      self.working_data.set_index(self.index, inplace=True)

    return features

  def get_features(self, attribute=None):
    """
    Creates a list of markers or polygons to be added to a FeatureGroup.
    Useful intermediary for show_map and also for Streamlit dashboards, which directly use FeatureGroups.
    """
    geom_type = self.working_data.geometry.geom_type.mode()[0] # Use the most common geometry

    scenario = "Reference"
    if attribute is not None:
      scenario = "Data"

    features = self.style_map(scenario=scenario, geom_type=geom_type, attribute=attribute)
    self.features[attribute] = features

    return features

  def show_map(self, attribute=None, other_data=None, title=None):
    """
    A map symbolizing the attribute.

    Contextual information can be added by specifying points and polygons

    attribute should be a column in the geodataframe self.data
    self.data should be a geodataframe
    other_data should be a geodataframe or list of geodataframes

    title = TBD

    Returns a folium.Map
    """
    this_map = folium.Map(tiles="cartodb positron")

    # Set up FeatureGroup
    fg = folium.FeatureGroup(name=attribute)
    features = self.get_features(attribute) # If attribute is none, then reference (show_map)
    for feature in features:
      fg.add_child(feature)

    # Show other data (should be a self.features...)
    if other_data is not None:
      for feature in other_data:
        fg.add_child(feature)
    fg.add_to(this_map)

    # compute boundaries so that the map automatically zooms in
    bounds = this_map.get_bounds()
    this_map.fit_bounds(bounds, padding=0)

    return this_map

class Facilities(Charts, Maps):
  """
  A facility by facility view
  There are different ways of getting facilities (NPRI_IDs, spatial query near, place = a mailing address...)
  ids -- list of NPRI_IDs like [1, 15, 2412]
  near -- list of lat,lng like [lat,lng]
  place -- list of FSA(s) to match facilities on like ['N1E', 'N1H']
  across -- string of province
  substances -- list of substances
  bounds -- list of [[NW], [SE]] coords - xmin, ymin, xmax, ymax
  sql -- a sql query
  attributes -- True, returns all fields from the table. Otherwise, a list of column names like ["geom"]
  """
  def __init__(self, ids=None, near=None, place=None, across=None, substances=None, bounds=None, sql=None, attributes=None): #
    self.index = "NpriID"

    args = locals()
    del args["self"] # remove self
    #print(args) # Debugging
    params = parameterize(args)
    #print(params) # Debugging

    try:
      self.data, self.url, self.report_url = get_npri_data(view="facilities", endpoint="api", params=params, index=self.index) # Go to Flask
      print("final url: ", self.url, "report: ", self.report_url)
      self.data['geometry'] = geopandas.GeoSeries.from_wkb(self.data['geom'])
      self.data.drop("geom", axis=1, inplace=True)
      self.data = geopandas.GeoDataFrame(self.data, crs=3347)
      self.working_data = self.data.copy()
      self.features = {} # For storing saved maps
    except:
      print("ST something went wrong")

class Places(Charts, Maps):
  """
  A view from regions (DA, CSD, CD, Province/Territory, Canada)

  TODO: add basic info like province to npri_screen
  string of province
  """
  def __init__(self, ids=None, near=None, across=None):
    self.index = "dauid"

    args = locals()
    del args["self"] # remove self
    #print(args) # Debugging
    params = parameterize(args)
    #print(params) # Debugging

    try:
      self.data, self.url, self.report_url = get_npri_data(view="places", endpoint="api", params=params, index=self.index)
      print("final url: ", self.url, "report: ", self.report_url)
      self.data['geometry'] = geopandas.GeoSeries.from_wkb(self.data['geom'])
      self.data.drop("geom", axis=1, inplace=True)
      self.data = geopandas.GeoDataFrame(self.data, crs=3347)
      self.working_data = self.data.copy()
      self.features = {} # For storing saved maps
    except:
      print("ST something went wrong")

class Companies(Charts):
  """
  A view from companies
  """
  def __init__(self, companies):
    self.index = "CompanyId"

    args = locals()
    del args["self"] # remove self
    #print(args) # Debugging
    params = parameterize(args)
    #print(params) # Debugging

    try:
      self.data, self.url, self.report_url = get_npri_data(view="company", endpoint="api", params=params, index=self.index)
      print("final url: ", self.url, "report: ", self.report_url)
      self.working_data = self.data.copy()
    except:
      print("Error") # Convert to error

class Substances(Charts):
  """
  A view from companies
  """
  def __init__(self, pollutants):
    self.index = "Substance"

    args = locals()
    del args["self"] # remove self
    #print(args) # Debugging
    params = parameterize(args)
    #print(params) # Debugging

    try:
      self.data, self.url, self.report_url = get_npri_data(view="substance", endpoint="api", params=params, index=self.index)
      print("final url: ", self.url, "report: ", self.report_url)
      self.working_data = self.data.copy()
    except:
      print("Error") # Convert to error

class Industries(Charts):
  """
  A view from companies
  """
  def __init__(self, industries):
    self.index = "NAICSPrimary"

    args = locals()
    del args["self"] # remove self
    #print(args) # Debugging
    params = parameterize(args)
    #print(params) # Debugging

    try:
      self.data, self.url, self.report_url = get_npri_data(view="industry", endpoint="api", params=params, index=self.index)
      print("final url: ", self.url, "report: ", self.report_url)
      self.working_data = self.data.copy()
    except:
      print("Error") # Convert to error

class Times(Charts):
  """
  A view over time/for a specific year(s) for facility(s)[TBD], region(s), company(s), or substance(s)
  view - should be one of time_place (history_da_table), time_substance (history_substance_table), time_company (history_company_table)
  years - optional time frame specified in a list like [2015, 2020] (inclusive, so 2015 through 2020)
  """
  def __init__(self, view, years):
    
    args = locals()
    del args["self"], args["view"] # remove self and in the case of Times, the view
    #print(args) # Debugging
    params = parameterize(args)
    #print(params) # Debugging

    indexes = {"time_company": 'CompanyID',"time_place": 'DA', "time_substance": 'Substance'} # How to avoid duplicating this?
    self.index = indexes[view]

    try:
      self.data, self.url, self.report_url = get_npri_data(view=view, endpoint="api", params=params, index=self.index) #
      print("final url: ", self.url, "report: ", self.report_url)
      self.working_data = self.data.copy()
    except:
      print("Error") # Convert to error

  def aggregate(self, how = "sum", attribute = "Quantity", unit = "tonnes"): # Defaults for aggregation (can be overriden)
    """
    A function to aggregate Times data
    """
    try:
      self.working_data = self.data.loc[self.data["Units"]==unit]
      results = self.data.groupby(by=self.index)[[attribute]].agg(how)
      self.working_data = results
    except:
      print("Error") # Convert to error
