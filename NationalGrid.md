# Introduction #

The CurrentCost GUI can access realtime data from the National Grid and display this on the live CurrentCost graph.

# Details #
## National electricity demand ##
![http://currentcostgui.googlecode.com/files/cc_nationalgrid.png](http://currentcostgui.googlecode.com/files/cc_nationalgrid.png)

The first feature implemented was to display the UK **national electricity demand** on the live graph. This can either be displayed by itself, or overlaid on the same graph as your personal CurrentCost live data.

  * National Grid data is shown in blue
  * Personal CurrentCost data is shown in red

Start the graph from:

> Download data --> Show live national electricity demand
## National electricity supply vs demand ##
![http://currentcostgui.googlecode.com/files/cc_nationalgrid2.png](http://currentcostgui.googlecode.com/files/cc_nationalgrid2.png)

The latest feature implemented is to display the UK **national electricity supply vs demand** on the live graph. This can either be displayed by itself, or overlaid on the same graph as your personal CurrentCost live data.

  * National Grid data is shown in blue:
    * if this blue line is below the green line, then the UK demand is currently outstripping supply and more generation is needed to meet demand;
    * if this blue line is above the green line, then the UK supply exceeds the current demand.
  * Personal CurrentCost data is shown in red

Start the graph from:

> Download data --> Show live National Grid supply vs demand

# Implementation #

The data is obtained by screen-scaping http://www.nationalgrid.com

You can see http://www.nationalgrid.com/uk/Electricity/Data/Realtime/Demand/Demand60.htm for their own representation.

Screen-scraping is naturally a somewhat brittle approach - any changes to the National Grid website will break the app. However, it's an interesting data source while it's available.