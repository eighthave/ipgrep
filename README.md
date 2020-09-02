ipgrep
======

`ipgrep` extracts possibly obfuscated host names and IP addresses from text,
resolves host names, and prints them, sorted by ASN.

Example:

```bash
$ ipgrep
hxxp://lifeiscalling-sports[.]com/8759j3f434 - 199[.]88[.]59[.]22
mebdco .com - teyseerlab,com. - meow://www.]adgroup.]ae/8759j3f434
Be careful with www.rumbafalcon\.com, it used to serve malware
```
returns
```csv
107.180.51.235	teyseerlab.com.	AS26496: AS-26496-GO-DADDY-COM-LLC - GoDaddy.com, LLC (US)
166.62.10.29	mebdco.com	AS26496: AS-26496-GO-DADDY-COM-LLC - GoDaddy.com, LLC (US)
23.229.237.128	lifeiscalling-sports.com	AS26496: AS-26496-GO-DADDY-COM-LLC - GoDaddy.com, LLC (US)
199.88.59.22	-	AS40539: PROHCI - Hosting Consulting, Inc (US)
162.252.57.82	www.rumbafalcon.com.	AS47869: NETROUTING-AS (NL)
194.170.187.46	www.adgroup.ae	AS5384: EMIRATES-INTERNET Emirates Internet (AE)
```

This is a trivial Python script, but I use it **a lot**, so I figured it might
be useful to others.

Dependencies:
```bash
$ pip install pycares
```


Ensuring complete results
-------------------------

By default, speed of execution is prioritized over completeness: by
default, each query will timeout after 5 seconds and will only be
retried once.  If completeness is more important, then use the command
line flags to increase those values.



Speeding up large runs
----------------------

Large amounts of DNS queries can take a long time to resolve.
`ipgrep` already uses asynchronous DNS to help with that.  When
running `ipgrep` on many files, then things can be sped up by an order
of magnitude by running a local caching recursive resolver like
[unbound](https://www.unbound.org/).

On a Debian-ish machine, that means just:

```console
$ sudo apt-get install unbound
```
