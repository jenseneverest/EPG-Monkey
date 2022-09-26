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
eg: `10.0.1.200:8087`

Running the python app in Windows will not work!

# Support

I have been using this personally for several months without any issues and decided to share it.

Any grabber issues should be directed to the guys over at [iptv-org](https://github.com/iptv-org/epg).
This is simply a GUI, scheduler, translator, combiner, server for the grabbers they maintain.

[![](https://www.paypalobjects.com/en_GB/i/btn/btn_donate_LG.gif)](https://www.paypal.com/donate/?hosted_button_id=62MYXSBT75D4E)

# Screenshots
![image](https://user-images.githubusercontent.com/5328818/192340712-21187930-7681-48f5-8443-e4891f75d1c6.png)
![image](https://user-images.githubusercontent.com/5328818/192341236-ea7f38d7-a50e-4253-be1b-e1405597d525.png)
![image](https://user-images.githubusercontent.com/5328818/192341911-a0e29ca3-07c2-42b1-b717-f1c8d33a654d.png)
![image](https://user-images.githubusercontent.com/5328818/192341512-e20de1fe-ad48-4c58-aef2-f569e119a91b.png)


