## What is MQTT? ##
MQTT is a messaging protocol, the specification for which can be found at http://mqtt.org/

## Why does the app support MQTT? ##
Many users of the CurrentCost GUI app already had their CurrentCost meters connected to a [Really Small Message Broker](http://www.alphaworks.ibm.com/tech/rsmb) for other purposes. Rather than need to disconnect their meters from the Broker in order to use the GUI, there was a demand for this application to connect to the CurrentCost meter via the Broker.

This also brought the benefit that the application could be used remotely - you don't even need to be at home to see the latest data from your CurrentCost meter.

## What do you need to get the MQTT support in the app to work? ##
The short version... this feature requires a third-party Python module that I am not able to re-distribute. If you work for IBM, you can get it for yourself from IIOSB. Unzip the files from there into the same directory as the CurrentCost app.

The longer version... I wanted an implementation of the MQTT client protocol for Python. Rather than write it from scratch, I reused an implementation written by other IBM employees.

We have an internal code hosting service, essentially a SourceForge-type thing, but hosted on our intranet. It's used so IBM developers can share and reuse code across the company. The developers of the MQTT client made their code available on this internal open source code site, so I was able to use it.

I am not able to redistribute their work outside of IBM. This is why I made the MQTT support an optional element in the application - and if the MQTT client is not present, the MQTT features in the app are all automatically disabled.

I'm very sorry for the inconvenience, but if you are not an IBM employee, then you will not be able to access this code, and so cannot use the MQTT features of the app.

If you are a developer, then you could implement it yourself based on the published specification, but I admit this isn't exactly ideal. Sorry.