import urllib2
from xml.etree.ElementTree import parse, dump

API_KEY = "2a7381c68a7b50cde9d9befac535c395"
REQ_URL = "http://ws.audioscrobbler.com/2.0/?method=track.getinfo&api_key={0}&artist=muse&track=sunburn"

req = REQ_URL.format(API_KEY)

resp = urllib2.urlopen(req)
resp = parse(resp)

print [e.text for e in resp.findall("track/album/image") if e.get("size") == "large"][0]
