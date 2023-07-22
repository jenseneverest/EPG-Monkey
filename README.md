# EPG Monkey

EPG Monkey is a GUI manager and server for the excellent [iptv-org](https://github.com/iptv-org/epg) grabbers!

- Select indiviual channels per guide
- Choose how many days to grab
- All guides are merged
- Translate programme titles and descriptions
- Updates daily at select hour
- Serves merged XMLTV guide

# Docker
Docker is the only supported way to run this

```
docker create \
--name=EPG-Monkey \
--restart=always \
-e TZ=Europe/London \
-p 8087:8001 \
-v /mnt/containers/EPG-Monkey:/config \
chris230291/epg-monkey:latest
```

After creating the Docker container find the web UI @ `<Docker Host IP>:<Port>`

# Support
Any grabber issues should be directed to the guys over at [iptv-org](https://github.com/iptv-org/epg).
This is simply a GUI, scheduler, translator, combiner, server for the grabbers they maintain.
