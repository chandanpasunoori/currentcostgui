This is a placeholder page - in time, this will be filled out with more detail.

# Step 1 - Download the app #
You can either [download the application](http://code.google.com/p/currentcostgui/downloads/list) as:
  * a set of Python scripts, suitable for Windows, Linux, or (_I think!_) Mac
  * a compiled Windows executable

# Step 2 - Install the app #
If you've gone for the compiled Windows executable, this should just involve unzipping everything you downloaded, making sure that the directory structure is all the same. Then run currentcost.exe

If you're going for the Python scripts, this still involves unzipping, and then running currentcost.py. But you'll probably hit at least a few ImportErrors where I've used a third-party library that you've not got.

If you have easy\_install, this shouldn't be a problem - the ImportError will tell you which module was missing, and easy\_install should know how to install it for you. A few tries of that was all I needed to do to get it running on my Ubuntu box.

You can get a [list of the prereq Python modules here](http://code.google.com/p/currentcostgui/wiki/Prerequisites).

# Step 3 - Run the app #
The app stores your history data on your local computer, so the first time you run it you will be asked where you want to store that database file. Future runs can just default to re-opening that database again.

# Step 4 - Connect to your CurrentCost meter #
Download data -> Download history (connect directly)

Then tell it the COM port number to use. (e.g. "COM3" if you're on Windows)

It should default to this value again in future. After successfully connecting, it should start drawing you graphs!