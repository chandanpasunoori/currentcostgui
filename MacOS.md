# Introduction #

Taken from comments on http://dalelane.co.uk/blog/?p=297

At some point, I'll write this into clearer guidance, but in the meantime thought it was useful to share even in this form.

There are also some step-by-step instructions available here http://nicktaylor.co.uk/2009/02/18/my-first-electricity-graph/ that look like they are worth trying.

# Details #

A few people have reported that running Python on Mac OS can be a bit of a pain. I don't have access to a Mac to try this for myself, but I'll add any useful advice I get from Mac OS owners to this page.

Please do add to this page if you figure something out that might help the next person to try!

[Addy:](http://dalelane.co.uk/blog/?p=297&cpage=1#comment-100135)
<blockquote>after many late night hours of hacking on my x86 iMac MAC OS X 10.5 (Leopard) I finally managed to get the currentcost.py GUI up and running! I don’t yet have the data cable, so can’t say whether it fully works yet.<br>
<br>
But I tried so many different Python and framework installs, I’m still not sure which one actually did the trick. In the end I stuck with the supplied Mac OS python (2.5.4) and used the Scipy Superpack script from;<br>
<br>
<a href='http://macinscience.org/?page_id=6'>http://macinscience.org/?page_id=6</a>

I guess this also installed wxpython ?<br>
Certainly I had no luck with easy_install of wxpython which fails even under Ubuntu Linux. I think the wxpython tarball doesn’t have a top level setup.py script ?<br>
<br>
The final issue I had was with the pysqlite module which used a missing sqlite3 dynamic library symbol. In the end I had to replace the system sqlite3 dynamic library in /usr/lib with one I rebuilt under MacPorts. Yuk!</blockquote>

[Addy:](http://dalelane.co.uk/blog/?p=297&cpage=1#comment-100141)
<blockquote>...it seems to be running now, I reverted the system libsqlite library and exported DYLD_LIBRARY_PATH instead, because my console log was filling up with dyld errors.<br>
The Mac OS X serial device is /dev/tty.usbserial ...</blockquote>

[Addy:](http://dalelane.co.uk/blog/?p=297&cpage=1#comment-100171)
<blockquote>I eventually solved the missing symbols in the libsqlite library by rebuilding the MacPorts sqlite3 package. I found some instructions on how to do this by pasting the missing symbol error into Google.<br>
Then once the MacPorts library was rebuilt I exported DYLD_LIBRARY_PATH to pick up the new MacPorts library under /opt. But I am still using the Mac OS X python binary.</blockquote>

[Addy:](http://dalelane.co.uk/blog/?p=297&cpage=1#comment-100172)
<blockquote>I just found the webpage with the ‘fix’ for rebuilding the MacPorts sqlite3 package;<br>
<br>
<a href='http://oss.itsystementwicklung.de/trac/pysqlite/ticket/238'>http://oss.itsystementwicklung.de/trac/pysqlite/ticket/238</a>

<code>port install sqlite3 +loadable_extensions</code>

I was seeing the <code>_sqlite3_enable_load_extension</code> symbol not being found error.</blockquote>