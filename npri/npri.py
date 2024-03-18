# -*- coding: utf-8 -*-

## Dependencies and Imports
import pandas
import folium
import geopandas
import numpy
import urllib.parse
import warnings
warnings.simplefilter(action='ignore', category=FutureWarning)

## Get Data
def get_data(sql, index = None):
  """
  generic data-getting function
  establishes a connection to the google database
  at the moment, relies on access to a secret password...
  executes sql against the database
  sql: string - a properly constructed postgresql query that will return data from the database
  """

  url= 'http://34.130.52.201/index.php?query='
  data_location=url+urllib.parse.quote_plus(sql)
  print(data_location)
  data = None
  try:
    data = pandas.read_csv(data_location)
    # Set index, if specified
    if index is not None:
      data.set_index(index, inplace=True)
  except:
    print("Error: We are unable to get the data. This may be because we've temporarily turned off the database to save money. If you'd like to keep using this tool, email enost[at]uoguelph[dot]ca to let us know!")

  return data

## Classes
class Maps():
  """
  A class that provides basic functions for classes with mappable data (Facilities, Places)
  """

  def style_map(self, scenario, geom_type, attribute=None):
    """
    A function to style map features.
    Scenarios: markers (w and w/o data), polygons (w and w/o data)
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
    
  def show_map(self, attribute=None, other_data = None):
    """
    A map symbolizing the attribute.

    Contextual information can be added by specifying points and polygons

    attribute should be a column in the geodataframe self.data
    self.data should be a geodataframe
    other_data should be a geodataframe or list of geodataframes

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


class Filters():
  def filters(self, attribute=None, operator=None, value=None, reset=False):
    """
    This function sets the working data to a filter of the overall data (or resets working data to the originally queried data)
    """
    if reset:
      self.working_data = self.data
    elif operator == "==":
      self.working_data = self.data.loc[self.data[attribute] == value]
    elif operator == ">=":
      self.working_data = self.data.loc[self.data[attribute] >= value]
    elif operator == "=<":
      self.working_data = self.data.loc[self.data[attribute] <= value]
    return self.working_data

  def missingness(self, attribute):
    """
    This function calculates the extent to which a dataset is missing data.
    Simply put, it calculates the percentage of NA in a given column.
    """
    pandas.options.mode.use_inf_as_na = True
    df = self.working_data[[attribute]]
    df = df.replace(r'^\s*$', numpy.nan, regex=True) # '' = na
    nans = df[[attribute]].isna().sum()[0] # See: https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.isna.html
    pct = (nans/self.working_data[[attribute]].shape[0]) * 100
    return pct


class Tables():
  def __init__(self, view, value = None):
    self.view = view
    self.value = value # Any particular industry(s)/company(s)/substance(s) to focus on. Does a text search.
    preset_indexes = {"industry": "NAICSPrimary", "company": "CompanyId", "substance": "SubstanceID"} # Move these presets elsewhere....
    preset_pretty = {"industry": "NAICSTitleEn", "company": "CompanyName", "substance": "Substance"}
    preset_views = {"industry": "npri_industry_table ", "company": "npri_companies_table ", "substance": "npri_tri_table "}
    self.sql = 'select * from ' + preset_views[self.view]
    self.pretty = preset_pretty[self.view]
    self.index = preset_indexes[self.view] # Preset ID

    if value is not None:
      if type(value) == list:
        value = ','.join('\'%%'+x.lower()+'%%\'' for x in value)
        print(value)
        self.sql += 'where lower("'+self.pretty+'") like any (array['+value+'])'
      else:
        self.sql += 'where lower("'+self.pretty+'") like \'%%'+value.lower()+'%%\''
    else:
      pass # get all
      #print("The unit parameter must be one of the following....") # Convert to error


class SpatialTables():
  def __init__(self, view, ids=None, near=None, place=None, across=None):
    self.view = view
    preset_indexes = {"facilities": "NpriID", "places": "dauid"}
    presets_pid = {"facilities": {"AB":1,"BC":2,"MB":3,"NB":4,"NL":5,"NT":6,"NS":7,"NU":8,"ON":9,"PE":10,"QC":11,"SK":12,"YT":13},
                   "places": {"AB":48,"BC":59,"MB":46,"NB":13,"NL":10,"NT":61,"NS":12,"NU":62,"ON":35,"PE":11,"QC":24,"SK":47,"YT":60}}
    preset_views = {"facilities": "npri_exporter_table ", "places": "npri_screen_table "}
    self.sql = 'select * from ' + preset_views[self.view]
    self.index = preset_indexes[self.view] # Preset ID

    #print(ids)
    if ids is not None:
      if type(ids) == list:
        id_list = 'where "'+self.index+'" in ({})'.format(','.join(str(idx) for idx in ids))
        self.sql += id_list
      else:
        self.sql += 'where "'+self.index+'" = '+ids

    elif near is not None:
      if type(near) == list:
        self.sql += "where ST_INTERSECTS(geom,ST_Buffer(ST_Transform(ST_SetSRID(ST_MakePoint("+str(near[1])+", "+str(near[0])+"), 4326), 3347), 10000));" # A default 10 km buffer of the lat,lng provided
      else:
        print("You need to provide a list with one lat / long pair e.g [43.5,-80.25]")

    elif place is not None: # Currently only have FSAs not Address City Names. Only used for Facilities/NPRI_EXPORTER
      if type(place) == list:
        self.sql += 'where "ForwardSortationArea" in ({})'.format(','.join('\''+str(fsa)+'\'' for fsa in place))
      else:
        print("You need to provide a list of FSA(s) (first three digits of a postal code) e.g. ['N1E', 'N1H']")

    elif across is not None: # Province
      across = presets_pid[view][across]
      self.sql += 'where "ProvinceID" = '+str(across)

    else:
      self.sql += 'limit 5' # Prevent empty calls like Places() from querying the whole db



class Facilities(SpatialTables, Charts, Maps, Filters):
  """
  A facility by facility view
  There are different ways of getting facilities (NPRI_IDs, spatial query near, place = a mailing address...)
  ids -- NPRI_IDs list like [1, 15, 2412]
  near -- list of lat,lng like [lat,lng]
  place -- list of FSA(s) to match facilities on like ['N1E', 'N1H']
  across -- string of province
  """
  def __init__(self, ids=None, near=None, place=None, across=None):
    super().__init__(view = "facilities", ids=ids, near=near, place=place, across=across)
    try:
      print(self.sql, self.index) # Debugging
      self.data = get_data(self.sql, self.index)
      self.data['geometry'] = geopandas.GeoSeries.from_wkb(self.data['geom'])
      self.data.drop("geom", axis=1, inplace=True)
      self.data = geopandas.GeoDataFrame(self.data, crs=3347)
      self.working_data = self.data.copy()
      self.features = {} # For storing saved maps
    except:
      print("ST something went wrong")



class Places(SpatialTables, Charts, Maps, Filters):
  """
  A view from regions (DA, CSD, CD, Province/Territory, Canada)

  TODO: add basic info like province to npri_screen
  string of province
  """
  def __init__(self, ids=None, near=None, across=None):
    super().__init__(view = "places", ids=ids, near=near, across=across)
    try:
      print(self.sql, self.index) # Debugging
      self.data = get_data(self.sql, self.index)
      self.data['geometry'] = geopandas.GeoSeries.from_wkb(self.data['geom'])
      self.data.drop("geom", axis=1, inplace=True)
      self.data = geopandas.GeoDataFrame(self.data, crs=3347)
      self.working_data = self.data.copy()
      self.features = {} # For storing saved maps
    except:
      print("ST something went wrong")


class Companies(Tables, Charts, Filters):
  """
  A view from companies
  """
  def __init__(self, value):
    super().__init__(view = "company", value = value)
    try:
      print (self.sql, self.index) # Debugging
      self.data = get_data(self.sql, self.index)
      self.working_data = self.data.copy()
    except:
      print("Error") # Convert to error


class Industries(Tables, Charts, Filters):
  """
  A view from companies
  """
  def __init__(self, value):
    super().__init__(view = "industry", value = value)
    try:
      print (self.sql, self.index) # Debugging
      self.data = get_data(self.sql, self.index)
      self.working_data = self.data.copy()
    except:
      print("Error") # Convert to error


class Substances(Tables, Charts, Filters):
  """
  A view from substances

  TODO: add cas to NPRI_TRI?
  """
  def __init__(self, value):
    super().__init__(view = "substance", value = value)  # Sql-ify
    try:
      print (self.sql, self.index) # Debugging
      self.data = get_data(self.sql, self.index)
      self.working_data = self.data.copy()
    except:
      print("Error") # Convert to error


class Times(Charts):
  """
  A view over time/for a specific year(s) for facility(s)[TBD], region(s), company(s), or substance(s)
  history_substance
  history_company
  history_da
  """
  def __init__(self, kind, years = None):
    self.kind = kind # Should be a particular view e.g. history_da, history_company
    self.years = years # Should be a list like [2010, 2020] that is a start/stop pair, inclusive
    self.sql = 'select * from '

    if kind.lower() == "company":
      self.sql += 'history_company_table '
      self.index = "CompanyID"
    elif kind.lower() == "region":
      self.sql += 'history_da_table '
      self.index = "DA"
    elif kind.lower() == "substance":
      self.sql += 'history_substance_table '
      self.index = "Substance"
    else:
      print("The unit parameter must be one of the following....") # Convert to error

    try:
      if years:
        self.sql += 'where "ReportYear" >=' + str(years[0]) + ' and "ReportYear" <=' + str(years[1])
      print (self.sql, self.index) # Debugging
      self.data = get_data(self.sql, self.index)
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

