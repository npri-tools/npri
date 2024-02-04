# npri
A Python package providing easy-to-use code that returns recently reported emissions from facilities, socio-economic information for places, emissions records for specific companies and industries, and emissions trends over time

## Installation and Basic Usage
```
pip install npri
from npri import npri
```

In this first example, we will search for information about a place using a geographic coordinate (latitude and longitude). We set the `near` argument equal to a list containing these coordinates. The object that is returned has a `data` property that lets us see the information as a dataframe.
```
this_place = npri.Places(near=[43.25, -80])
this_place.data
```

| C10_RATE_TOTAL | total_co_2022 | total_so2_2022 | total_ammonia_2022 | total_pm10_2022 | total_pm25_2022 | total_no2_2022 | total_voc_2022 | releases_to_air_2022 | sum_years | ... | NumberOfSubstances_Percentile | NumberOfMedia | NumberOfMeasureMethods | NumberOfVOCs_Distinct | NumberOfVOCs | NumberOfPAHs | Substances | CAS | ProvinceID | geometry |                                                   |
|---------------:|--------------:|---------------:|-------------------:|----------------:|----------------:|---------------:|---------------:|---------------------:|----------:|----:|------------------------------:|--------------:|-----------------------:|----------------------:|-------------:|-------------:|-----------:|----:|-----------:|---------:|---------------------------------------------------|
|          dauid |               |                |                    |                 |                 |                |                |                      |           |     |                               |               |                        |                       |              |              |            |     |            |          |                                                   |
|    35240402    |          14.6 |            NaN |                NaN |             NaN |             NaN |            NaN |            NaN |                  NaN |       NaN | NaN |                           ... |           NaN |                    NaN |                   NaN |          NaN |          NaN |        NaN | NaN |        NaN |       35 | MULTIPOLYGON (((7190549.646 883345.754, 719068... |
|    35250030    |          10.0 |            NaN |                NaN |             NaN |             NaN |            NaN |            NaN |                  NaN |       NaN | NaN |                           ... |           NaN |                    NaN |                   NaN |          NaN |          NaN |        NaN | NaN |        NaN |       35 | MULTIPOLYGON (((7188523.526 879491.143, 718834... |
|    35250031    |           0.0 |            NaN |                NaN |             NaN |             NaN |            NaN |            NaN |                  NaN |       NaN | NaN |                           ... |           NaN |                    NaN |                   NaN |          NaN |          NaN |        NaN | NaN |        NaN |       35 | MULTIPOLYGON (((7191376.191 880328.200, 719150... |
|    35250032    |          11.8 |            NaN |                NaN |             NaN |             NaN |            NaN |            NaN |                  NaN |       NaN | NaN |                           ... |           NaN |                    NaN |                   NaN |          NaN |          NaN |        NaN | NaN |        NaN |       35 | MULTIPOLYGON (((7188368.631 878414.126, 718828... |
|    35250033    |           9.5 |            NaN |                NaN |             NaN |             NaN |            NaN |            NaN |                  NaN |       NaN | NaN |                           ... |           NaN |                    NaN |                   NaN |          NaN |          NaN |        NaN | NaN |        NaN |       35 | MULTIPOLYGON (((7188267.523 877771.920, 718762... |

Many of the values here are `NaN` indicating that the dissemination area saw none of these pollutants (CO, SO2, and other "criteria air contaminants") reporting being released to the air in 2022. This is not to say that the dissemination area does not experience air pollution, but simply that there are no NPRI-reporting facilities in it that reported releases of those pollutants in 2022.
