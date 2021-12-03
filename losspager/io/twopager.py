# stdlib imports
import os
from datetime import datetime
from collections import OrderedDict
from math import log10
import logging

# third party imports
from impactutils.textformat.text import pop_round_short, round_to_nearest
from impactutils.textformat.text import dec_to_roman
from impactutils.colors.cpalette import ColorPalette
from impactutils.comcat.query import ComCatInfo
from impactutils.io.cmd import get_command_output
import numpy as np

LATEX_TO_PDF_BIN = "pdflatex"

LATEX_SPECIAL_CHARACTERS = OrderedDict(
    [
        ("\\", "\\textbackslash{}"),
        ("{", "\{"),
        ("}", "\}"),
        ("#", "\#"),
        ("$", "\$"),
        ("%", "\%"),
        ("&", "\&"),
        ("^", "\\textasciicircum{}"),
        ("_", "\_"),
        ("~", "\textasciitilde{}"),
    ]
)

DEFAULT_PAGER_URL = "http://earthquake.usgs.gov/data/pager/"
DEFAULT_FEMA_URL = "gis.fema.gov"
MIN_DISPLAY_POP = 1000
LOSS_CONV = 1000


def texify(text):
    newtext = text
    for original, replacement in LATEX_SPECIAL_CHARACTERS.items():
        newtext = newtext.replace(original, replacement)
    return newtext


def create_twopager(pdata, hazinfo, version_dir):
    """
    :param pdata:
      PagerData object.
    :param hazinfo:
      HazusInfo object.
    :param version_dir:
      Path of event version directory.
    """

    # ---------------------------------------------------------------------------
    # Sort out some paths
    # ---------------------------------------------------------------------------

    # Location of this module
    mod_dir, dummy = os.path.split(__file__)

    # losspager package direcotry
    losspager_dir = os.path.join(mod_dir, "..")

    # Repository root directory
    root_dir = os.path.join(losspager_dir, "..")

    # Logos directory
    logos_dir = os.path.join(losspager_dir, "logos")

    # twopager latex template file
    template_file = os.path.join(logos_dir, "twopager.tex")

    # ---------------------------------------------------------------------------
    # Read in pager data, Hazus data, and latex template
    # ---------------------------------------------------------------------------

    json_dir = os.path.join(version_dir, "json")
    pdict = pdata._pagerdict
    edict = pdata.getEventInfo()

    with open(template_file, "r") as f:
        template = f.read()

    # ---------------------------------------------------------------------------
    # Fill in template values
    # ---------------------------------------------------------------------------

    # Sort out origin time
    olat = edict["lat"]
    olon = edict["lon"]
    otime_utc = edict["time"]
    date_utc = datetime.strptime(otime_utc, "%Y-%m-%d %H:%M:%S")

    date_local = pdata.local_time
    DoW = date_local.strftime("%a")
    otime_local = date_local.strftime("%H:%M:%S")
    otime_local = DoW + " " + otime_local
    template = template.replace("[ORIGTIME]", otime_utc)
    template = template.replace("[LOCALTIME]", otime_local)

    # Some paths
    template = template.replace("[VERSIONFOLDER]", version_dir)
    template = template.replace("[HOMEDIR]", root_dir)

    # Magnitude location string under USGS logo
    magloc = f"M {edict['mag']:.1f}, {texify(edict['location'])}"
    template = template.replace("[MAGLOC]", magloc)

    # Pager version
    ver = "Version " + str(pdict["pager"]["version_number"])
    template = template.replace("[VERSION]", ver)

    # Epicenter location
    lat = edict["lat"]
    lon = edict["lon"]
    dep = edict["depth"]
    if lat > 0:
        hlat = "N"
    else:
        hlat = "S"
    if lon > 0:
        hlon = "E"
    else:
        hlon = "W"
    template = template.replace("[LAT]", f"{abs(lat):.4f}")
    template = template.replace("[LON]", f"{abs(lon):.4f}")
    template = template.replace("[HEMILAT]", hlat)
    template = template.replace("[HEMILON]", hlon)
    template = template.replace("[DEPTH]", f"{dep:.1f}")

    # Tsunami warning? --- need to fix to be a function of tsunamic flag
    if edict["tsunami"]:
        template = template.replace(
            "[TSUNAMI]", "FOR TSUNAMI INFORMATION, SEE: tsunami.gov"
        )
    else:
        template = template.replace("[TSUNAMI]", "")

    # Elapsed time
    if pdata.isScenario():
        elapse = ""
    else:
        elapse = "Created: " + pdict["pager"]["elapsed_time"] + " after earthquake"
    template = template.replace("[ELAPSED]", elapse)

    # Summary alert color
    template = template.replace("[SUMMARYCOLOR]", pdata.summary_alert.capitalize())
    template = template.replace("[ALERTFILL]", pdata.summary_alert)

    # Summary comment
    template = template.replace("[IMPACT1]", texify(pdict["comments"]["impact1"]))
    template = template.replace("[IMPACT2]", texify(pdict["comments"]["impact2"]))

    # Hazus arrow color and relative position
    hazdel = (hazinfo.hazloss) / LOSS_CONV
    if hazdel < 0.1:
        hazdelval = 0.1
    elif hazdel > 1000000:
        hazdelval = 1000000
    else:
        hazdelval = hazdel
    arrowloc = ((6 - log10(hazdelval)) * 0.83) - 0.07

    # distance (in cm) to the left from right end of the econ histogram
    template = template.replace("[ARROWSHIFT]", f"{arrowloc:.2f}")
    shift = arrowloc + 1.75
    # value is ARROWSHIFT plus 1.75
    # white box around the arrow and text to "open" the lines between values
    template = template.replace("[BOXSHIFT]", f"{shift:.2f}")
    # color of the Hazus econ loss value using PAGER color scale
    template = template.replace("[HAZUS_SUMMARY]", hazinfo.summary_color)

    # MMI color pal
    pal = ColorPalette.fromPreset("mmi")

    # get all of the tag tables
    (green_tag_table, yellow_tag_table, red_tag_table) = hazinfo.createTaggingTables()

    # Building Tags by occupancy
    template = template.replace("[GREEN_TAG_TABLE]", green_tag_table)
    template = template.replace("[YELLOW_TAG_TABLE]", yellow_tag_table)
    template = template.replace("[RED_TAG_TABLE]", red_tag_table)

    # Direct economic losses table
    econ_losses_table = hazinfo.createEconTable()
    template = template.replace("[DEL_TABLE]", econ_losses_table)

    # Non-fatal injuries table
    injuries_table = hazinfo.createInjuryTable()
    template = template.replace("[NFI_TABLE]", injuries_table)

    # Shelter needs table
    shelter_table = hazinfo.createShelterTable()
    template = template.replace("[SHELTER_TABLE]", shelter_table)

    # Earthquake Debris table
    debris_table = hazinfo.createDebrisTable()
    template = template.replace("[DEBRIS_TABLE]", debris_table)

    eventid = edict["eventid"]

    # query ComCat for information about this event
    # fill in the url, if we can find it
    try:
        ccinfo = ComCatInfo(eventid)
        eventid, allids = ccinfo.getAssociatedIds()
        event_url = ccinfo.getURL() + "#pager"
    except:
        event_url = DEFAULT_PAGER_URL

    eventid = "Event ID: " + eventid
    template = template.replace("[EVENTID]", texify(eventid))
    template = template.replace("[EVENTURL]", texify(event_url))
    template = template.replace("[HAZUSURL]", texify(DEFAULT_FEMA_URL))

    # Write latex file
    tex_output = os.path.join(version_dir, "twopager.tex")
    with open(tex_output, "w") as f:
        f.write(template)

    pdf_output = os.path.join(version_dir, "twopager.pdf")
    stderr = ""
    try:
        cwd = os.getcwd()
        os.chdir(version_dir)
        cmd = "%s -interaction nonstopmode --output-directory %s %s" % (
            LATEX_TO_PDF_BIN,
            version_dir,
            tex_output,
        )
        logging.info(f"Running {cmd}...")
        res, stdout, stderr = get_command_output(cmd)
        os.chdir(cwd)
        if not res:
            if os.path.isfile(pdf_output):
                msg = "pdflatex created output file with non-zero exit code."
                return (pdf_output, msg)
            return (None, stderr)
        else:
            if os.path.isfile(pdf_output):
                return (pdf_output, stderr)
            else:
                pass
    except Exception as e:
        pass
    finally:
        os.chdir(cwd)
    return (None, stderr)
