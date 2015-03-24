
---

## "The application connects to the CurrentCost meter then seems to wait for data forever" ##
Are you sure you have a second generation CurrentCost monitor?

This application was written to display the historical electricity usage data collected by second-generation CurrentCost meters.

First generation CurrentCost meters do not store (and therefore cannot output) history data.

So the application may be waiting for history data which your meter will never send.

If this is the case, then this application will not work with your meter.

Unfortunately, I have not had access to a first generation meter to be able to program the application to automatically recognise when it is connected to one. So if you want to confirm it, you need to get access to the data your meter is producing yourself. You can do this using [freely available code](http://code.google.com/p/currentcost/), or using a serial port monitor such as Hyperterminal.

Note that the older meters do still output the current reading, so your alternative would be to store this. If you store every reading, every 6 seconds, you can build up a history data source of your own. Several of us have done this - [I've blogged about doing this with MySQL myself, using Perl to query the MySQL store](http://dalelane.co.uk/blog/?p=272). You can do some quite powerful queries this way.

The downside is that to build a useful history store, you have to have a computer connected to the CurrentCost meter all the time. Which can potentially negate any benefits of monitoring your electricity usage!

You can use a very low-powered server (I [use a Slug for this purpose](http://dalelane.co.uk/blog/?p=267)).

As the newer CurrentCost meters store limited history data on the device themselves, I wrote this Python app to use this - for people who didn’t want the overhead of having a server running all the time!

---

## "Will this app work with the new CC128 meters?" ##
Yes. See [CC128](CC128.md)

---

## "Which Windows COM port should I connect to?" ##
This depends on the software driver you are using to connect your CurrentCost meter to your computer. If you use the Prolific driver linked to on the [Prerequisites page](http://code.google.com/p/currentcostgui/wiki/Prerequisites) then the COM port for your cable is specified in Device Manager:

![http://currentcostgui.googlecode.com/files/devicemanager.png](http://currentcostgui.googlecode.com/files/devicemanager.png)

The [prereqs page](http://code.google.com/p/currentcostgui/wiki/Prerequisites) includes more info on config for the serial driver.

---

## "Where do I get the MQTT library the app talks about?" ##
Please see [the documentation about the MQTT feature](MQTT.md)

---

## "How do I get the Python scripts to work on my Mac?" ##
A few people have reported that running Python on Mac OS can be a bit of a pain. I don't have access to a Mac to try this for myself, but I'm keeping a copy of any [useful advice I get from Mac OS owners](MacOS.md).

Please do add to this page if you figure something out that might help the next person to try!

---

## "What's the 'Sync with web' thing about?" ##
Please see the [detailed doc about this feature](CompareYourData.md)

---

## "When I try to run the compiled Windows exe version, it crashes on startup with an exception in 'ModName: numpy.core.dotblas.pyd'" ##
The CurrentCost app is actually a Python script. The "proper" (or at least reliable) way to run it is to run the actual Python script source with [a Python interpreter](http://www.python.org/download/).

I know that a lot of people wont have Python, and will be reluctant or unable to install it just for this app. So I also make available a version packaged using [py2exe](http://www.py2exe.org/).

Check out the py2exe website if you want to know what this is all about, but in short, it bundles together a Python interpreter with the script and any required third party modules. So you get the whole lot in one self-contained (and huge!) bundle.

Nice in theory, but in practice, py2exe has issues. And one of them is that it doesn't seem to play nicely with numpy (one of the third party Python modules used in my app) on some computers.

Three people have reported this problem - but after repeated attempts to resolve it, I've not been able to come up with an answer.

My issue is that the crash doesn't happen in my code - it happens when Windows tries to initialise the numpy module when starting the built-in Python interpreter that py2exe has bundled. So there isn't anything I can change in my code that will effect this. And my efforts to make changes to the py2exe building haven't made any difference.

All this is a long-winded way of saying that you have a few options:

a) Install Python and run the script manually

b) Run the py2exe-built version on another computer (most WinXP computers seem to be okay with it... I have no idea what is different for the few that seem to crash with it)

c) Download my script, and py2exe. And build it into an executable yourself. Then tell me how you did it so I can fix my version ;-)

Sorry I don't have any more helpful answers - I've put a lot of time into investigating this before, and am completely stumped.

---

## "Why does it take so long to download history data from the CC128?" ##
Short version - that's how long it takes the CC128 meter to output history data, sorry.

Long version - I've [discussed this on my blog](http://dalelane.co.uk/blog/?p=456) but it seems that the CC128 doesn't output it's history in a single XML message. It splits it up into multiple messages. And there is a high level of redundancy in the messages - consecutive messages have overlapping copies of the data, so it does take a long time for it to output the whole history. I'm seeing output times of over ten minutes for a meter with 14 days of history stored. There is nothing my app can do to speed this up - sorry.

---
