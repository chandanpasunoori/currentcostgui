
---

# Python #
> Note: This only applies if you download the Python source. If you download the compiled Windows executable, you wont need to get Python separately, or any of the third-party Python modules listed here.

The biggest prerequisite is Python, as this is a Python application. I use Python 2.6, but you can probably use newer versions.

The app also uses a number of third-party Python modules:
  * matplotlib
  * numpy
  * scipy
  * pyserial
  * pysqlite
  * pywin32
  * simplejson
  * wxpython

Most of these can be installed using easy install
E.g.
```
easy_install wxpython
```

Alternatively, some platforms provide a platform-specific way to install the modules, such as on Ubuntu, I use commands such as:
```
sudo aptitude install python-serial 
```

Such approaches saves having to manually download and install each of the prereqs.

This is how I install the pre-requisites for use on my Windows machine (note the order - as some of these are dependent on others):

  * install ActivePython for Windows (including Python Package Manager and the Windows-specific packages) - version 2.6.4.8 from http://www.activestate.com/activepython/
  * install scipy using scipy-0.7.1-win32-superpack-python2.6.exe from http://sourceforge.net/projects/scipy/files/
  * install numpy using numpy-1.4.0rc1-win32-superpack-python2.6.exe from http://sourceforge.net/projects/numpy/files/
  * install matplotlib using matplotlib-0.99.1.win32-py2.6.exe from http://sourceforge.net/projects/matplotlib/files/
  * install wxPython using wxPython2.8-win32-unicode-2.8.10.1-py26.exe from http://sourceforge.net/projects/wxpython/files/
  * install pysqlite using pysqlite-2.5.6.win32-py2.6.exe from http://code.google.com/p/pysqlite/downloads/list
  * install pyserial using pyserial-2.5-rc1.win32.exe from http://sourceforge.net/projects/pyserial/files/
  * use pypm to install simplejson (2.0.9-1) - using `pypm install simplejson`


---

# Serial drivers #

If you are using Windows, you will need software drivers for the cable you use to connect your CurrentCost meter to your computer. I use Prolific drivers that I downloaded from http://www.prolific.com.tw/eng/downloads.asp?ID=31 and configured them like this:

![http://currentcostgui.googlecode.com/files/prolificsettings.png](http://currentcostgui.googlecode.com/files/prolificsettings.png)

If you are using Linux, then there is useful guidance on Ubuntu settings available at http://www.linuxuk.org/CurrentCost_Ubuntu

---

# CurrentCost #

This application was written to receive data from [CurrentCost home electricity usage monitors](http://dalelane.co.uk/blog/?p=265).

These are given away for free by many electricity companies, and can also be [bought on eBay](http://stores.ebay.co.uk/Current-Cost-Ltd).

---
