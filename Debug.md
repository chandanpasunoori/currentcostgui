# Introduction #

The app includes basic logging for errors and diagnostics, to help developers identify the source of problems.

# Details #

There are two ways to collect diagnostics:
  * From startup - when starting the application, use the `--debug` option
  * From the GUI - click on 'Help -> Collect diagnostics' to start it collecting. Click on the menu item again to stop it.

The diagnostics file is called currentcostdiagnostics.log and should be written to the same folder as the currentcost software.

In the event of an error, error reports should be written to this file even if diagnostics collection is not enabled.