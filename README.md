# WiFi Bandwidth Assessement and Visualization Tool

![](report-cover-image.png)
*Screenshot of WiFi bandwidth heat map*

## Summary
    
The intent of this project was to assess the bandwidth of the Eduroam wifi
network around a select area of the UC Davis campus. A systematic series 
of speed tests were performed where along with the results, the GPS 
coordinates, and correlated signal strength and quality were recorded 
as well. Once the data was gathered, statistical analysis along several metrics
was was conducted and the bandwidth test results were visualized as a heat map.

## Report

The [final report](Final-Report.pdf) details project scope, program
development, testing procedures, and subsequent statistical analysis and
data visualization.

### Heat Map Visualization

Download bandwidth [heat map](https://csiflabs.cs.ucdavis.edu/~mhankins/downloadHeatmap.html)  
Upload bandwidth [heat map](https://csiflabs.cs.ucdavis.edu/~mhankins/uploadHeatmap.html)

## Dependencies

The following modules are necessary to use this tool:

* [getch](https://pypi.org/project/getch/)
* [iwlib](https://github.com/nathan-hoad/python-iwlib)
* [Pynmea2](https://github.com/Knio/pynmea2)
* [Pythonwifi](https://git.tuxfamily.org/pythonwifi/pythonwifi.git/)
* [Speedtest-cli](https://github.com/sivel/speedtest-cli)
* [wifi](https://wifi.readthedocs.io/en/latest/index.html)

## GPS Source

An Android phone running
[BlueNMEA](https://max.kellermann.name/projects/blue-nmea/) serves GPS
NMEA sentences via a TCP port. The Android debugging bridge (ADB) is used
to locally map that port to a Linux host where the script runs.

## Usage

The script takes the WiFi interface name as its only argument. The `eduroam`
SSID is set statically in the script. Main operation is driven by a
self-explanatory menu system.
