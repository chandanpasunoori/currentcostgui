# What does the feature do? #
![http://farm3.static.flickr.com/2640/3829077175_2fa45c1c04.jpg](http://farm3.static.flickr.com/2640/3829077175_2fa45c1c04.jpg)

Your live electricity usage data can be combined with the "energy mix" of ratios of different generation methods used in the UK National Grid.

This shows what proportion of your electricity came from each energy source:

  * Closed cycle gas turbine
  * Open cycle gass turbine
  * Oil
  * Coal
  * Nuclear
  * Wind
  * Pump storage
  * Non-pump storage hydro
  * Other
  * International import: France
  * International import: Ireland

(list of energy sources taken from [amee.com](http://wiki.amee.com/index.php/Real_Time_Electricity))

The data is shown as a stacked graph, with horizontal bands of colour showing how much of each source of energy you've used.

# How do you use it? #
  1. Start collecting live electricity usage (e.g. Show live data --> Connect via serial port)
  1. When prompted, click on 'Yes' to say that you do want the app to download information about the "energy mix" from the Internet ![http://currentcostgui.googlecode.com/files/cc_gen_q.png](http://currentcostgui.googlecode.com/files/cc_gen_q.png)
  1. Click on 'Show live data' --> 'National electricity generation' to display the stacked graph

## Notes: ##
  * This will show the generation sources of live electricity usage up until this point. Clicking on 'Show live data' --> 'National electricity generation' will redraw the graph with the latest live usage data
  * If you answered 'No', to prevent the app from downloading usage information, the graph will show the live data with everything from 'UNKNOWN'
![http://currentcostgui.googlecode.com/files/cc_gen_unknown.png](http://currentcostgui.googlecode.com/files/cc_gen_unknown.png)
  * If you change your mind, stop and start the live data graph so that the app asks you the question again. You can do this as often as you like. The periods where you answered 'No' will just be shown as 'UNKNOWN'
![http://currentcostgui.googlecode.com/files/cc_gen_stopstart.png](http://currentcostgui.googlecode.com/files/cc_gen_stopstart.png)