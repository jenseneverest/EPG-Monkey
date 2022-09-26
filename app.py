from flask import (
    Flask,
    render_template,
    redirect,
    request,
    Response,
    make_response,
    flash,
)
import xml.etree.cElementTree as ET
import os
import json
import concurrent.futures
import requests
from deep_translator import GoogleTranslator
from functools import wraps
import secrets
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
import string
import subprocess
import zipfile
import io
import logging

app = Flask(__name__)
app.secret_key = secrets.token_urlsafe(32)

logger = logging.getLogger("EPG-Monkey")
logger.setLevel(logging.INFO)
logFormat = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
fileHandler = logging.FileHandler("EPG-Monkey.log")
fileHandler.setFormatter(logFormat)
logger.addHandler(fileHandler)
consoleFormat = logging.Formatter("[%(levelname)s] %(message)s")
consoleHandler = logging.StreamHandler()
consoleHandler.setFormatter(consoleFormat)
logger.addHandler(consoleHandler)

basePath = os.path.dirname(os.path.realpath(__file__))

if os.getenv("CONFIG"):
    configDir = os.getenv("CONFIG")
else:
    configDir = basePath

configFile = os.path.join(configDir, "config.json")
xmlFile = os.path.join(configDir, "tv.xml")
grabberDir = os.path.join(basePath, "epg-master")
sitesDir = os.path.join(grabberDir, "sites")
tmpDir = os.path.join(basePath, "tmp")

languages = {
    "afrikaans": "af",
    "albanian": "sq",
    "amharic": "am",
    "arabic": "ar",
    "armenian": "hy",
    "azerbaijani": "az",
    "basque": "eu",
    "belarusian": "be",
    "bengali": "bn",
    "bosnian": "bs",
    "bulgarian": "bg",
    "catalan": "ca",
    "cebuano": "ceb",
    "chichewa": "ny",
    "chinese (simplified)": "zh-CN",
    "chinese (traditional)": "zh-TW",
    "corsican": "co",
    "croatian": "hr",
    "czech": "cs",
    "danish": "da",
    "dutch": "nl",
    "english": "en",
    "esperanto": "eo",
    "estonian": "et",
    "filipino": "tl",
    "finnish": "fi",
    "french": "fr",
    "frisian": "fy",
    "galician": "gl",
    "georgian": "ka",
    "german": "de",
    "greek": "el",
    "gujarati": "gu",
    "haitian creole": "ht",
    "hausa": "ha",
    "hawaiian": "haw",
    "hebrew": "iw",
    "hindi": "hi",
    "hmong": "hmn",
    "hungarian": "hu",
    "icelandic": "is",
    "igbo": "ig",
    "indonesian": "id",
    "irish": "ga",
    "italian": "it",
    "japanese": "ja",
    "javanese": "jw",
    "kannada": "kn",
    "kazakh": "kk",
    "khmer": "km",
    "kinyarwanda": "rw",
    "korean": "ko",
    "kurdish": "ku",
    "kyrgyz": "ky",
    "lao": "lo",
    "latin": "la",
    "latvian": "lv",
    "lithuanian": "lt",
    "luxembourgish": "lb",
    "macedonian": "mk",
    "malagasy": "mg",
    "malay": "ms",
    "malayalam": "ml",
    "maltese": "mt",
    "maori": "mi",
    "marathi": "mr",
    "mongolian": "mn",
    "myanmar": "my",
    "nepali": "ne",
    "norwegian": "no",
    "odia": "or",
    "pashto": "ps",
    "persian": "fa",
    "polish": "pl",
    "portuguese": "pt",
    "punjabi": "pa",
    "romanian": "ro",
    "russian": "ru",
    "samoan": "sm",
    "scots gaelic": "gd",
    "serbian": "sr",
    "sesotho": "st",
    "shona": "sn",
    "sindhi": "sd",
    "sinhala": "si",
    "slovak": "sk",
    "slovenian": "sl",
    "somali": "so",
    "spanish": "es",
    "sundanese": "su",
    "swahili": "sw",
    "swedish": "sv",
    "tajik": "tg",
    "tamil": "ta",
    "tatar": "tt",
    "telugu": "te",
    "thai": "th",
    "turkish": "tr",
    "turkmen": "tk",
    "ukrainian": "uk",
    "urdu": "ur",
    "uyghur": "ug",
    "uzbek": "uz",
    "vietnamese": "vi",
    "welsh": "cy",
    "xhosa": "xh",
    "yiddish": "yi",
    "yoruba": "yo",
    "zulu": "zu",
}

hours = {
    "00:00": 0,
    "01:00": 1,
    "02:00": 2,
    "03:00": 3,
    "04:00": 4,
    "05:00": 5,
    "06:00": 6,
    "07:00": 7,
    "08:00": 8,
    "09:00": 9,
    "10:00": 10,
    "11:00": 11,
    "12:00": 12,
    "13:00": 13,
    "14:00": 14,
    "15:00": 15,
    "16:00": 16,
    "17:00": 17,
    "18:00": 18,
    "19:00": 19,
    "20:00": 20,
    "21:00": 21,
    "22:00": 22,
    "23:00": 23,
}

config = {}


def authorise(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        settings = config["settings"]
        security = settings["security"]
        username = settings["username"]
        password = settings["password"]
        if (
            security == "false"
            or auth
            and auth.username == username
            and auth.password == password
        ):
            return f(*args, **kwargs)
        return make_response(
            "Could not verify your login!",
            401,
            {"WWW-Authenticate": 'Basic realm="Login Required"'},
        )

    return decorated


def updateGrabbers():
    logger.info("Updating Grabbers...")

    r = requests.get("https://github.com/iptv-org/epg/archive/refs/heads/master.zip")
    z = zipfile.ZipFile(io.BytesIO(r.content))
    z.extractall(basePath)
    ret = subprocess.call(
        ["npm", "install"],
        cwd=grabberDir,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    if ret == 0:
        logger.info("Grabbers updated!")
    else:
        logger.info("Updating Grabbers Failed!")

    return ret


def getGrabbers():
    def getData(xml):
        path = xml
        id = os.path.basename(xml).split(".channels")[0]
        site = os.path.basename(xml).split("_")[0]
        country = xml.split("_")[1].split(".c")[0].upper()
        channels = []

        tree = ET.parse(path)
        root = tree.getroot()
        for channel in root.findall(".//channel"):
            name = channel.text
            lang = channel.attrib["lang"]
            xmltv_id = channel.attrib["xmltv_id"]
            channels.append({"name": name, "lang": lang, "xmltv_id": xmltv_id})

        data = {
            id: {"path": path, "site": site, "country": country, "channels": channels}
        }

        grabbers.update(data)

    if not os.path.exists(grabberDir):
        updateGrabbers()

    xmls = []

    for r, d, f in os.walk(sitesDir):
        for file in f:
            if ".channels.xml" in file:
                xmls.append(os.path.join(r, file))

    grabbers = {}

    with concurrent.futures.ThreadPoolExecutor() as executor:
        executor.map(getData, xmls)

    return grabbers


def getConfig():
    try:
        with open(configFile) as f:
            data = json.load(f)
    except:
        print("Creating config file")
        data = {}

    data.setdefault("sites", {})
    data.setdefault("settings", {})
    data["settings"].setdefault("update hour", 12)
    data["settings"].setdefault("days to grab", 2)
    data["settings"].setdefault("translate titles", "false")
    data["settings"].setdefault("translate descriptions", "false")
    data["settings"].setdefault("translate language", "en")
    data["settings"].setdefault("translate proxy", "")
    data["settings"].setdefault("security", "false")
    data["settings"].setdefault("username", "admin")
    data["settings"].setdefault("password", "12345")

    with open(configFile, "w") as f:
        json.dump(data, f, indent=4)

    return data


def makeXmltv():
    def grabXmltv(site):
        def translateProgramme(programme):
            proxies = {"http": translateProxy, "https": translateProxy}

            if translateTitles == "true":
                try:
                    title = programme.find("title")
                    channel = programme.attrib["channel"]
                    try:
                        titleLang = title.attrib["lang"]
                    except:
                        title.set("lang", langs.get(channel))
                        titleLang = title.attrib["lang"]
                    titleText = title.text

                    if titleLang != translateLangauge:
                        titleTranslated = GoogleTranslator(
                            source=titleLang, target=translateLangauge, proxies=proxies
                        ).translate(titleText)

                        titleTranslated = string.capwords(titleTranslated, " ")

                        ET.SubElement(
                            programme, "title", lang=translateLangauge
                        ).text = str(titleTranslated)
                except:
                    pass

            if translateDescriptions == "true":
                try:
                    desc = programme.find("desc")
                    channel = programme.attrib["channel"]
                    try:
                        descLang = desc.attrib["lang"]
                    except:
                        desc.set("lang", langs.get(channel))
                        descLang = desc.attrib["lang"]
                    descText = desc.text

                    if descLang != translateLangauge:
                        descTranslated = GoogleTranslator(
                            source=descLang, target=translateLangauge, proxies=proxies
                        ).translate(descText)

                        ET.SubElement(
                            programme, "desc", lang=translateLangauge
                        ).text = str(descTranslated)
                except:
                    pass

        siteId = site["id"]
        wantedChannels = site["wanted channels"]
        customNames = site.get("custom names", {})

        for r, d, f in os.walk(sitesDir):
            for file in f:
                if siteId + ".channels.xml" in file:
                    channelsXml = os.path.join(r, file)
                    directory = os.path.dirname(os.path.join(r, file))
                    for file in os.listdir(directory):
                        if file.endswith(".config.js"):
                            conf = os.path.join(directory, file)
                            break
                    break
            else:
                continue
            break

        tree = ET.parse(channelsXml)
        root = tree.getroot()
        channels = root.find("channels")
        langs = {}
        for elem in list(channels):
            if elem.attrib.get("xmltv_id", "") in wantedChannels:
                xmltv_id = elem.attrib.get("xmltv_id", "")
                lang = elem.attrib.get("lang", "")
                langs.update({xmltv_id: lang})
                customName = customNames.get(xmltv_id)
                if customName:
                    elem.text = customName
            else:
                channels.remove(elem)

        tmpChannels = os.path.join(tmpDir, siteId + ".channels.xml")
        output = os.path.join(tmpDir, siteId + ".guide.xml")

        tree.write(tmpChannels)

        if os.path.exists(tmpChannels):

            # subprocess.call(["npx", "epg-grabber", "--days=" + str(days), "--config=" + conf, "--channels=" + tmpChannels,
            #                "--output=" + output], shell=True, cwd=grabberDir, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

            with subprocess.Popen(
                [
                    "npx",
                    "epg-grabber",
                    "--days=" + str(days),
                    "--config=" + conf,
                    "--channels=" + tmpChannels,
                    "--output=" + output,
                ],
                cwd=grabberDir,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
            ) as grab:
                for line in iter(grab.stdout.readline, ""):
                    line = line.decode("unicode-escape")
                    if line.startswith("["):
                        logger.info(line.rstrip())
                    if grab.poll() is not None:
                        break

            logger.info("Finished grabbing channels for {}".format(siteId))

            if os.path.exists(os.path.join(tmpDir, output)):
                tree = ET.parse(os.path.join(tmpDir, output))

                if translateTitles == "true" or translateDescriptions == "true":
                    logger.info("Translating programmes for {}...".format(siteId))

                    root = tree.getroot()
                    programmes = root.findall("programme")
                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        executor.map(translateProgramme, programmes)

                    logger.info("Finished translating programmes for {}".format(siteId))

                return tree

    logger.info("Starting XMLTV Update...")

    wanted = []
    totalChannels = 0

    for i in config["sites"]:
        id = i
        wantedChannels = config["sites"][i].get("enabled channels", [])
        custonNames = config["sites"][i].get("custom names", {})
        totalChannels = totalChannels + len(wantedChannels)
        if wantedChannels:
            wanted.append(
                {
                    "id": id,
                    "wanted channels": wantedChannels,
                    "custom names": custonNames,
                }
            )

    if len(wanted) == 0:
        logger.info("No enabled channels. XMLTV update stopping")
        return

    logger.info(
        "EPG-Monkey found {} enabled channels across {} grabbers".format(
            totalChannels, len(wanted)
        )
    )

    updateGrabbers()

    # clean folder first
    for f in os.listdir(tmpDir):
        os.remove(os.path.join(tmpDir, f))

    days = config["settings"]["days to grab"]
    translateTitles = config["settings"]["translate titles"]
    translateDescriptions = config["settings"]["translate descriptions"]
    translateLangauge = config["settings"]["translate language"]
    translateProxy = config["settings"]["translate proxy"]

    logger.info(
        "Config: Days={} - Translate Titles={} - Translate Descriptions={} - Translation Language={} - Translation Proxy={}".format(
            days,
            translateTitles,
            translateDescriptions,
            translateLangauge,
            translateProxy,
        )
    )

    with concurrent.futures.ThreadPoolExecutor() as executor:
        results = executor.map(grabXmltv, wanted)

    logger.info("Building final XMLTV...")

    root = ET.Element("tv")
    xmltv = ET.ElementTree(root)
    channels = []
    programmes = []

    for result in results:
        try:
            channels = channels + result.findall("channel")
            programmes = programmes + result.findall("programme")
        except:
            pass

    for channel in channels:
        root.append(channel)

    for programme in programmes:
        root.append(programme)

    root.set("days", str(days))
    root.set("translateTitles", translateTitles)
    root.set("translateDescriptions", translateDescriptions)
    root.set("translateLanguage", translateLangauge)
    root.set("created", datetime.now().strftime("%d/%m/%Y %H:%M:%S"))

    ET.indent(xmltv, space="\t", level=0)
    xmltv.write(xmlFile)

    # clean folder
    for f in os.listdir(tmpDir):
        os.remove(os.path.join(tmpDir, f))

    logger.info("Finished XMLTV Update!")


@app.route("/", methods=["GET"])
@authorise
def home():
    return redirect("/sites", code=302)


@app.route("/sites", methods=["GET"])
@authorise
def sites():
    sites = getGrabbers()

    # ID's can change so cleanup neccasary
    for site in sites:
        availableChannels = []
        enabledChannels = (
            config.get("sites", {}).get(site, {}).get("enabled channels", [])
        )
        customNames = config.get("sites", {}).get(site, {}).get("custom names", {})
        for channel in sites[site]["channels"]:
            availableChannels.append(channel["xmltv_id"])
        for channel in list(enabledChannels):
            if channel not in availableChannels:
                logger.info(
                    "Removing {} from {} as it no longer exists".format(channel, site)
                )
                config["sites"][site]["enabled channels"] = list(
                    filter((channel).__ne__, enabledChannels)
                )
        for channel in list(customNames):
            if channel not in availableChannels:
                logger.info(
                    "Removing {} from {} custom channel names as it no longer exists".format(
                        channel, site
                    )
                )
                customNames.pop(channel, None)

        sites[site]["enabled channels"] = len(enabledChannels)

    with open(configFile, "w") as f:
        json.dump(config, f, indent=4)

    return render_template("sites.html", sites=sites)


@app.route("/site/<id>", methods=["GET"])
@authorise
def site(id):
    site = getGrabbers()[id]
    enabledChannels = config["sites"].get(id, {}).get("enabled channels", [])
    customNames = config["sites"].get(id, {}).get("custom names", {})

    return render_template(
        "site.html",
        site=site,
        siteId=id,
        enabledChannels=enabledChannels,
        customNames=customNames,
    )


@app.route("/site/save", methods=["POST"])
@authorise
def saveSite():
    global config

    siteId = request.form["siteId"]
    enabledEdits = json.loads(request.form["enabledEdits"])
    nameEdits = json.loads(request.form["nameEdits"])

    enabledChannels = config["sites"].get(siteId, {}).get("enabled channels", [])
    customNames = config["sites"].get(siteId, {}).get("custom names", {})

    for edit in enabledEdits:
        if edit["enabled"]:
            enabledChannels.append(edit["channel id"])
        else:
            enabledChannels = list(filter((edit["channel id"]).__ne__, enabledChannels))

    for edit in nameEdits:
        channelId = edit["channel id"]
        CustomName = edit["custom name"]
        if CustomName != "":
            customNames[channelId] = CustomName
        else:
            customNames.pop(channelId, None)

    config["sites"].setdefault(siteId, {})
    config["sites"][siteId]["enabled channels"] = sorted(enabledChannels)
    config["sites"][siteId]["custom names"] = dict(sorted(customNames.items()))

    with open(configFile, "w") as f:
        json.dump(config, f, indent=4)

    logger.info("{} config saved!".format(siteId))
    flash("{} Config Saved!".format(siteId), "success")

    return redirect("/site/" + siteId, code=302)


@app.route("/site/reset", methods=["POST"])
@authorise
def resetSite():
    global config

    siteId = request.form["siteId"]

    config["sites"].setdefault(siteId, {})
    config["sites"][siteId]["enabled channels"] = []
    config["sites"][siteId]["custom names"] = {}

    with open(configFile, "w") as f:
        json.dump(config, f, indent=4)

    logger.info("{} config Reset!".format(siteId))
    flash("{} Config Reset!".format(siteId), "success")

    return redirect("/site/" + siteId, code=302)


@app.route("/settings", methods=["GET"])
@authorise
def settings():
    settings = config["settings"]
    nextUpdate = str(schedulerId).split("at: ")[1].rstrip(")")
    return render_template(
        "settings.html",
        settings=settings,
        nextUpdate=nextUpdate,
        languages=languages,
        hours=hours,
    )


@app.route("/settings/save", methods=["POST"])
@authorise
def saveSettings():
    global config
    updateHour = int(request.form["updateHour"])
    daysToGrab = int(request.form["daysToGrab"])
    translateTitles = request.form["translateTitles"]
    translateDescriptions = request.form["translateDescriptions"]
    translateLanguage = request.form["translateLanguage"]
    translateProxy = request.form["translateProxy"]
    security = request.form["security"]
    username = request.form["username"]
    password = request.form["password"]

    config["settings"] = {
        "translate titles": translateTitles,
        "days to grab": daysToGrab,
        "translate descriptions": translateDescriptions,
        "translate language": translateLanguage,
        "translate proxy": translateProxy,
        "update hour": updateHour,
        "security": security,
        "username": username,
        "password": password,
    }

    with open(configFile, "w") as f:
        json.dump(config, f, indent=4)

    schedulerId.reschedule("cron", hour=updateHour)

    logger.info("Settings saved!")
    flash("Settings Saved!", "success")

    return redirect("/settings", code=302)


@app.route("/xmltv", methods=["GET"])
@authorise
def xmltv():
    if not os.path.exists(xmlFile):
        return "No XMLTV. Configure channels and update the XMLTV."

    tree = ET.parse(xmlFile)
    root = tree.getroot()

    return Response(ET.tostring(root, encoding="unicode"), mimetype="text/xml")


@app.route("/update/xmltv", methods=["GET"])
@authorise
def updateXmltv():
    makeXmltv()

    flash("XMLTV Recreated!", "success")

    return redirect("/settings", code=302)


@app.route("/update/grabbers", methods=["GET"])
@authorise
def update():
    if updateGrabbers() == 0:
        flash("Grabbers Updated!", "success")
    else:
        flash("Updating grabbers failed!", "danger")

    return redirect("/sites", code=302)


@app.route("/log", methods=["GET"])
@authorise
def log():
    return render_template("log.html")


@app.route("/log/stream", methods=["GET"])
@authorise
def stream():
    with open("EPG-Monkey.log") as f:
        log = f.read()
    return log


if __name__ == "__main__":
    config = getConfig()

    scheduler = BackgroundScheduler(daemon=True)
    schedulerId = scheduler.add_job(
        makeXmltv, "cron", hour=config.get("settings", {}).get("update hour", 0)
    )
    scheduler.start()

    app.run(host="0.0.0.0", port=8001, debug=False)
