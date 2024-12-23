.. _satellite_packets:

Satellite packets 
=================

Cloudloop
---------
Cloudloop packets contain short burst data (SBD) payloads delivered via the Iridium network.  The Cloudloop packets contain additional metadata that pertains to the receiver where the packet was received, and the payload contains one or more 'SD card' packets.  

Cloudloop packets originate from a HTTP webhook event, configured via the https://data.cloudloop.com portal, or requested in CSV format from a web API.
This means that the packets have differing formats depending on their origin.

Webhook format (JSON)
^^^^^^^^^^^^^^^^^^^^^
Satellite packets delivered by webhook are in a JSON format called `LingoMO <https://knowledge.cloudloop.com/docs/lingo/mo>`_.

The message format has five top level fields (one top level and one sub fields not relevant to cryodecoder have been omitted):

* ID - Unique Identifier for each Message generated by the platform

* Received At - Time the Message was first received from the Network (UTC)

* Identity - Identifiers for this Thing in Cloudloop (e.g. Account, Subscriber, Device etc)

* Header - Transport-specific meta-data about the Message transmission
    
    * SBD - SBD specific meta-data (e.g. approximate location)

* Message - Raw Message payload sent from the Device in Bytes

Each LingoMO message contains unique and potentially useful information whcih we have to decide whether we discard or not.  We can store the ID, received timestamp, identity parameters directly in addition to logging the raw JSON for the SBD header field.

Within the CHIL ecosystem, the Webhook format is used by the cryodb server when accepting webhook requests.  The cryodecoder module could offer the following functionality:

* Parse JSON object into Python dictionary (simplest)

* Parse JSON object into Python object with no payload decoding

* Parse JSON object into Python object and perform payload decoding