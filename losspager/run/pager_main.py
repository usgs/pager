#!/usr/bin/env python

# local imports
from impactutils.transfer.emailsender import EmailSender
from impactutils.comcat.query import ComCatInfo
from mapio.shake import getHeaderData
from losspager.models.exposure import Exposure
from losspager.models.econexposure import EconExposure
from losspager.models.emploss import EmpiricalLoss
from losspager.models.semimodel import SemiEmpiricalFatality
from losspager.utils.country import Country
from losspager.utils.logger import PagerLogger
from losspager.utils.admin import PagerAdmin, split_event, transfer
from losspager.utils.exception import PagerException
from losspager.utils.datapath import get_data_path
from losspager.onepager.comment import get_impact_comments
from losspager.onepager.comment import get_structure_comment
from losspager.onepager.comment import get_secondary_comment
from losspager.onepager.comment import get_historical_comment
from losspager.onepager.onepager import create_onepager
from losspager.io.pagerdata import PagerData
from losspager.vis.impactscale import drawImpactScale
from losspager.vis.contourmap import draw_contour
from losspager.utils.config import read_config
from losspager.mail.formatter import format_exposure

# stdlib imports
import os.path
import sys
import re
import glob
import traceback
import io
import datetime
import shutil
import textwrap
from urllib import request
import tempfile
import socket
import logging

# third party imports
import matplotlib
import numpy as np

# this allows us to have a non-interactive backend - essential on systems
# without a display
matplotlib.use("Agg")


COUNTRY = Country()
TIMEFMT = "%Y-%m-%d %H:%M:%S"
TSUNAMI_MAG_THRESH = 7.3


def _is_url(gridfile):
    try:
        fh = request.urlopen(gridfile)
        tdir = tempfile.mkdtemp()
        grid_file = os.path.join(tdir, "grid.xml")
        data = fh.read().decode("utf-8")
        fh.close()
        f = open(grid_file, "wt")
        f.write(data)
        f.close()
        return (True, grid_file)
    except Exception:
        return (False, None)


def _check_pdl(gridfile, config):
    try:
        configfile = config["transfer"]["pdl"]["configfile"]
        configbase, configname = os.path.split(configfile)
        lines = open(configfile, "rt").readlines()
        index_on = False
        for line in lines:
            if line.find("[indexer_listener_exec_storage]") > -1:
                index_on = True
                continue
            if index_on:
                if line.find("directory") > -1:
                    parts = line.split("=")
                    storage_dir = parts[1].strip()
                    storage_parts = storage_dir.split(os.path.sep)
                    grid_file = os.path.join(
                        configbase,
                        storage_parts,
                        "shakemap",
                        gridfile,
                        "download",
                        "grid.xml",
                    )
                    if not os.path.isfile(grid_file):
                        return (False, None)
                    return (True, grid_file)
        return (False, None)
    except:
        return (False, None)


def _get_release_status(
    pargs, config, fatmodel, fatdict, ecomodel, ecodict, shake_tuple, event_folder
):
    # if we're not primary, it's released by default.
    # if our summary alert is green or yellow, it's released by default.
    # if the processing time is >= event time + 8(24?) hours, it's released by default.
    # if there is a "release" file in the event folder, it is released.
    # if the command line argument --release has been set, it is released.
    is_released = False

    # are we primary or secondary?
    if "status" not in config:
        is_released = True
    else:
        if config["status"] == "secondary":
            is_released = True

    # Are we at green or yellow
    fat_level = fatmodel.getAlertLevel(fatdict)
    eco_level = fatmodel.getAlertLevel(ecodict)
    if fat_level in ("green", "yellow") and eco_level in ("green", "yellow"):
        is_released = True

    # Are we past the release threshold?
    event_time = shake_tuple[1]["event_timestamp"]
    threshold_hours = datetime.timedelta(seconds=config["release_threshold"] * 3600)
    time_threshold = event_time + threshold_hours
    if datetime.datetime.utcnow() > time_threshold:
        is_released = True

    # Is there a "release" file in the event folder?
    release_file = os.path.join(event_folder, "release")
    if os.path.isfile(release_file):
        is_released = True

    # Has the release option been set?
    if pargs.release:
        is_released = True

    return is_released


def message_pager(config, onepager_pdf, doc):
    if "transfer" in config:
        if "status" in config and config["status"] == "primary":
            users = config["pager_team"]
            sender = config["mail_from"]
            hosts = config["mail_hosts"]
            subject = f"{doc.summary_alert.capitalize()} INTERNAL alert: {doc.location}"
            msg = (
                """This is an INTERNAL message notifying you of this %s alert.  You will receive a second message with the pending alert."""
                % doc.summary_alert
            )

            # create a string with exposure information
            exparray = doc.getTotalExposure()
            max_border_mmi = doc._pagerdict["population_exposure"]["maximum_border_mmi"]
            expstr = format_exposure(exparray, "long", max_border_mmi)

            msg += "\n" + expstr

            # remove unnecessary whitespace
            msg = textwrap.dedent(msg)

            props = {
                "recipients": users,
                "subject": subject,
                "sender": sender,
                "message": msg,
                "smtp_servers": hosts,
            }
            sender = EmailSender(props, local_files=[onepager_pdf])
            sender.send()


def _get_pop_year(event_year, popyears):
    pop_year = None
    tmin = 10000000
    popfile = None
    for popdict in popyears:
        popyear = popdict["population_year"]
        popgrid = popdict["population_grid"]
        if not os.path.isfile(popgrid):
            logging.warning(f"Population grid file {popgrid} does not exist.")
            sys.exit(1)
        if abs(popyear - event_year) < tmin:
            tmin = abs(popyear - event_year)
            pop_year = popyear
            popfile = popgrid
    return (pop_year, popfile)


def get_pager_version(eventfolder):
    pager_version = 1
    if not os.path.isdir(eventfolder):
        os.makedirs(eventfolder)
        last_version = 0
    else:
        allfolders = glob.glob(os.path.join(eventfolder, "version.*"))
        allfolders.sort()
        if len(allfolders):
            base, last_folder = os.path.split(allfolders[-1])
            last_version = int(re.findall("\d+", last_folder)[0])
        else:
            last_version = 0
    return last_version + 1


def _draw_probs(fatmodel, fatdict, ecomodel, ecodict, version_folder):
    fatG = fatmodel.getCombinedG(fatdict)
    fat_probs = fatmodel.getProbabilities(fatdict, fatG)
    fat_figure = drawImpactScale(fatdict, fat_probs, "fatality")

    ecoG = ecomodel.getCombinedG(ecodict)
    eco_probs = ecomodel.getProbabilities(ecodict, ecoG)
    eco_figure = drawImpactScale(ecodict, eco_probs, "economic")

    fat_probs_file = os.path.join(version_folder, "alertfatal.pdf")
    fat_probs_file_png = os.path.join(version_folder, "alertfatal.png")
    fat_probs_file_small = os.path.join(version_folder, "alertfatal_small.png")
    fat_probs_file_smaller = os.path.join(version_folder, "alertfatal_smaller.png")

    eco_probs_file = os.path.join(version_folder, "alertecon.pdf")
    eco_probs_file_png = os.path.join(version_folder, "alertecon.png")
    eco_probs_file_small = os.path.join(version_folder, "alertecon_small.png")
    eco_probs_file_smaller = os.path.join(version_folder, "alertecon_smaller.png")

    fat_figure.savefig(fat_probs_file, bbox_inches="tight")
    fat_figure.savefig(fat_probs_file_png, bbox_inches="tight")
    fat_figure.savefig(fat_probs_file_small, bbox_inches="tight", dpi=57)
    fat_figure.savefig(fat_probs_file_smaller, bbox_inches="tight", dpi=35)

    eco_figure.savefig(eco_probs_file, bbox_inches="tight")
    eco_figure.savefig(eco_probs_file_png, bbox_inches="tight")
    eco_figure.savefig(eco_probs_file_small, bbox_inches="tight", dpi=57)
    eco_figure.savefig(eco_probs_file_smaller, bbox_inches="tight", dpi=35)
    return (fat_probs_file, eco_probs_file)


def _cancel(eventid, config):
    event_source, event_source_code = split_event(eventid)
    msg = ""
    if "status" in config and config["status"] == "primary":
        if "transfer" in config:
            if "methods" in config["transfer"]:
                for method in config["transfer"]["methods"]:
                    if method not in config["transfer"]:
                        sys.stderr.write(
                            f"Method {method} requested but not configured...Skipping."
                        )
                        continue
                    params = config["transfer"][method]
                    if "remote_directory" in params:
                        vpath, vfolder = os.path.split(version_folder)
                        # append the event id and version folder to our pre-specified output directory
                        params["remote_directory"] = os.path.join(
                            params["remote_directory"], authid, vfolder
                        )
                    params["code"] = eventid
                    params["eventsource"] = event_source
                    params["eventsourcecode"] = event_source_code
                    params["magnitude"] = 0
                    params["latitude"] = 0
                    params["longitude"] = 0
                    params["depth"] = 0
                    params["eventtime"] = ""
                    sender_class = get_sender_class(method)
                    try:
                        if method == "pdl":
                            sender = sender_class(
                                properties=params,
                                local_directory=version_folder,
                                product_properties=product_params,
                            )
                        else:
                            sender = sender_class(
                                properties=params, local_directory=version_folder
                            )
                        try:
                            msg += sender.cancel()
                        except Exception as e:
                            msg += f"Failed to send products via PDL: {str(e)}"
                    except Exception as e:
                        msg += 'Could not send products via %s method - error "%s"' % (
                            method,
                            str(e),
                        )

    return msg


def main(pargs, config):
    # logfile = os.path.join(pager_folder, "pager.log")
    # plog = PagerLogger(logfile, [], "", "", debug=pargs.debug)
    # logger = plog.getLogger()
    # get the users home directory
    homedir = os.path.expanduser("~")
    # logger.info(f"Got home dir {homedir}.")

    # handle cancel messages
    # logger.info(f"cancel is {pargs.cancel}.")
    if pargs.cancel:
        # we presume that pargs.gridfile in this context is an event ID.
        msg = _cancel(pargs.gridfile, config)
        print(msg)
        return (True, msg)

    # what kind of thing is gridfile?
    is_file = os.path.isfile(pargs.gridfile)
    is_url, url_gridfile = _is_url(pargs.gridfile)
    is_pdl, pdl_gridfile = _check_pdl(pargs.gridfile, config)
    if is_file:
        gridfile = pargs.gridfile
    elif is_url:
        gridfile = url_gridfile
    elif is_pdl:
        gridfile = pdl_gridfile
    else:
        msg = f"ShakeMap Grid file {pargs.gridfile} does not exist."
        return (False, msg)

    pager_folder = os.path.join(homedir, config["output_folder"])
    pager_archive = os.path.join(homedir, config["archive_folder"])

    admin = PagerAdmin(pager_folder, pager_archive)

    # stdout will now be logged as INFO, stderr will be logged as WARNING
    mail_host = config["mail_hosts"][0]
    mail_from = config["mail_from"]
    developers = config["developers"]
    logfile = os.path.join(pager_folder, "pager.log")
    if pargs.logfile is not None:
        logfile = pargs.logfile

    plog = PagerLogger(logfile, developers, mail_from, mail_host, debug=pargs.debug)
    logger = plog.getLogger()

    try:
        eid = None
        pager_version = None
        # get all the basic event information and print it, if requested
        shake_tuple = getHeaderData(gridfile)
        eid = shake_tuple[1]["event_id"].lower()
        etime = shake_tuple[1]["event_timestamp"]
        if not len(eid):
            eid = shake_tuple[0]["event_id"].lower()
        network = shake_tuple[1]["event_network"].lower()
        if network == "":
            network = "us"
        if not eid.startswith(network):
            eid = network + eid
        logger.info(f"Got event ID {eid}.")

        # Create a ComcatInfo object to hopefully tell us a number of things about this event
        try:
            ccinfo = ComCatInfo(eid)
            location = ccinfo.getLocation()
            tsunami = ccinfo.getTsunami()
            authid, _ = ccinfo.getAssociatedIds()
        except Exception:  # fail over to what we can determine locally
            location = shake_tuple[1]["event_description"]
            tsunami = shake_tuple[1]["magnitude"] >= TSUNAMI_MAG_THRESH
            authid = eid

        # location field can be empty (None), which breaks a bunch of things
        if location is None:
            location = ""

        logger.info(f"Got authoritative ID {authid}.")

        # Check to see if user wanted to override default tsunami criteria
        if pargs.tsunami != "auto":
            if pargs.tsunami == "on":
                tsunami = True
            else:
                tsunami = False

        # check to see if this event is a scenario
        is_scenario = False
        shakemap_type = shake_tuple[0]["shakemap_event_type"]
        if shakemap_type == "SCENARIO":
            is_scenario = True
        logger.info(f"Scenario: {is_scenario}.")

        # if event is NOT a scenario and event time is in the future,
        # flag the event as a scenario and yell about it.
        if etime > datetime.datetime.utcnow():
            is_scenario = True
            logger.warning(
                "Event origin time is in the future! Flagging this as a scenario."
            )

        if is_scenario:
            if re.search("scenario", location.lower()) is None:
                location = "Scenario " + location

        # create the event directory (if it does not exist), and start logging there
        logger.info("Creating event directory")
        event_folder = admin.createEventFolder(authid, etime)
        logger.info(f"Created event folder {event_folder}.")

        # Stop processing if there is a "stop" file in the event folder
        stopfile = os.path.join(event_folder, "stop")
        if os.path.isfile(stopfile):
            fmt = '"stop" file found in %s.  Stopping processing, returning with 1.'
            logger.info(fmt % (event_folder))
            return True

        pager_version = get_pager_version(event_folder)
        version_folder = os.path.join(event_folder, "version.%03d" % pager_version)
        os.makedirs(version_folder)
        event_logfile = os.path.join(version_folder, "event.log")
        logger.info(f"Switching log to event log {event_logfile}.")

        # this will turn off the global rotating log file
        # and switch to the one in the version folder.
        plog.setVersionHandler(event_logfile)

        # Copy the grid.xml file to the version folder
        # sometimes (usu when testing) the input grid isn't called grid.xml.  Rename it here.
        version_grid = os.path.join(version_folder, "grid.xml")
        shutil.copyfile(gridfile, version_grid)

        # Check to see if the tsunami flag has been previously set
        tsunami_toggle = {"on": 1, "off": 0}
        tsunami_file = os.path.join(event_folder, "tsunami")
        if os.path.isfile(tsunami_file):
            tsunami = tsunami_toggle[open(tsunami_file, "rt").read().strip()]

        # get the rest of the event info
        etime = shake_tuple[1]["event_timestamp"]
        elat = shake_tuple[1]["lat"]
        elon = shake_tuple[1]["lon"]
        emag = shake_tuple[1]["magnitude"]

        # get the year of the event
        event_year = shake_tuple[1]["event_timestamp"].year

        # find the population data collected most closely to the event_year
        pop_year, popfile = _get_pop_year(
            event_year, config["model_data"]["population_data"]
        )
        logger.info("Population year: %i Population file: %s\n" % (pop_year, popfile))

        # Get exposure results
        logger.info("Calculating population exposure.")
        isofile = config["model_data"]["country_grid"]
        expomodel = Exposure(popfile, pop_year, isofile)
        exposure = None
        exposure = expomodel.calcExposure(gridfile)

        # incidentally grab the country code of the epicenter
        numcode = expomodel._isogrid.getValue(elat, elon)
        if np.isnan(numcode):
            cdict = None
        else:
            cdict = Country().getCountry(int(numcode))
        if cdict is None:
            ccode = "UK"
        else:
            ccode = cdict["ISO2"]

        logger.info(f"Country code at epicenter is {ccode}")

        # get fatality results, if requested
        logger.info("Calculating empirical fatalities.")
        fatmodel = EmpiricalLoss.fromDefaultFatality()
        fatdict = fatmodel.getLosses(exposure)

        # get economic results, if requested
        logger.info("Calculating economic exposure.")
        econexpmodel = EconExposure(popfile, pop_year, isofile)
        ecomodel = EmpiricalLoss.fromDefaultEconomic()
        econexposure = econexpmodel.calcExposure(gridfile)
        ecodict = ecomodel.getLosses(econexposure)
        shakegrid = econexpmodel.getShakeGrid()

        # Get semi-empirical losses
        logger.info("Calculating semi-empirical fatalities.")
        urbanfile = config["model_data"]["urban_rural_grid"]
        if not os.path.isfile(urbanfile):
            raise PagerException(f"Urban-rural grid file {urbanfile} does not exist.")

        semi = SemiEmpiricalFatality.fromDefault()
        semi.setGlobalFiles(popfile, pop_year, urbanfile, isofile)
        semiloss, resfat, nonresfat = semi.getLosses(gridfile)

        # get all of the other components of PAGER
        logger.info("Getting all comments.")
        # get the fatality and economic comments
        impact1, impact2 = get_impact_comments(
            fatdict, ecodict, econexposure, event_year, ccode
        )
        # get comment describing vulnerable structures in the region.
        struct_comment = get_structure_comment(resfat, nonresfat, semi)
        # get the comment describing historic secondary hazards
        secondary_comment = get_secondary_comment(elat, elon, emag)
        # get the comment describing historical comments in the region
        historical_comment = get_historical_comment(elat, elon, emag, exposure, fatdict)

        # generate the probability plots
        logger.info("Drawing probability plots.")
        fat_probs_file, eco_probs_file = _draw_probs(
            fatmodel, fatdict, ecomodel, ecodict, version_folder
        )

        # generate the exposure map
        exposure_base = os.path.join(version_folder, "exposure")
        logger.info("Generating exposure map...")
        oceanfile = config["model_data"]["ocean_vectors"]
        oceangrid = config["model_data"]["ocean_grid"]
        cityfile = config["model_data"]["city_file"]
        borderfile = config["model_data"]["border_vectors"]
        shake_grid = expomodel.getShakeGrid()
        pop_grid = expomodel.getPopulationGrid()
        pdf_file, png_file, mapcities = draw_contour(
            shake_grid,
            pop_grid,
            oceanfile,
            oceangrid,
            cityfile,
            exposure_base,
            borderfile,
            is_scenario=is_scenario,
        )
        logger.info(f"Generated exposure map {pdf_file}")

        # figure out whether this event has been "released".
        is_released = _get_release_status(
            pargs,
            config,
            fatmodel,
            fatdict,
            ecomodel,
            ecodict,
            shake_tuple,
            event_folder,
        )

        # Create a data object to encapsulate everything we know about the PAGER
        # results, and then serialize that to disk in the form of a number of JSON files.
        logger.info("Making PAGER Data object.")
        doc = PagerData()
        timezone_file = config["model_data"]["timezones_file"]
        elapsed = pargs.elapsed
        doc.setInputs(
            shakegrid,
            timezone_file,
            pager_version,
            shakegrid.getEventDict()["event_id"],
            authid,
            tsunami,
            location,
            is_released,
            elapsed=elapsed,
        )
        logger.info("Setting inputs.")
        doc.setExposure(exposure, econexposure)
        logger.info("Setting exposure.")
        doc.setModelResults(
            fatmodel, ecomodel, fatdict, ecodict, semiloss, resfat, nonresfat
        )
        logger.info("Setting comments.")
        doc.setComments(
            impact1, impact2, struct_comment, historical_comment, secondary_comment
        )
        logger.info("Setting map info.")
        doc.setMapInfo(cityfile, mapcities)
        logger.info("Validating.")
        doc.validate()

        # if we have determined that the event is a scenario (origin time is in the future)
        # and the shakemap is not flagged as such, set the shakemap type in the
        # pagerdata object to be 'SCENARIO'.
        if is_scenario:
            doc.setToScenario()

        json_folder = os.path.join(version_folder, "json")
        os.makedirs(json_folder)
        logger.info("Saving output to JSON.")
        doc.saveToJSON(json_folder)
        logger.info("Saving output to XML.")
        doc.saveToLegacyXML(version_folder)

        logger.info("Creating onePAGER pdf...")
        onepager_pdf, error = create_onepager(doc, version_folder)
        if onepager_pdf is None:
            raise PagerException(f"Could not create onePAGER output: \n{error}")

        # copy the contents.xml file to the version folder
        contentsfile = get_data_path("contents.xml")
        if contentsfile is None:
            raise PagerException("Could not find contents.xml file.")
        shutil.copy(contentsfile, version_folder)

        # send pdf as attachment to internal team of PAGER users
        if not is_released and not is_scenario:
            message_pager(config, onepager_pdf, doc)

        # run transfer, as appropriate and as specified by config
        # the PAGER product eventsource and eventsourcecode should
        # match the input ShakeMap settings for these properties.
        # This can possibly cause confusion if a regional ShakeMap is
        # trumped with one from NEIC, but this should happen less often
        # than an NEIC origin being made authoritative over a regional one.
        eventsource = network
        eventsourcecode = eid
        res, msg = transfer(
            config,
            doc,
            eventsourcecode,
            eventsource,
            version_folder,
            is_scenario=is_scenario,
        )
        logger.info(msg)
        if not res:
            logger.critical(f'Error transferring PAGER content. "{msg}"')

        print(f"Created onePAGER pdf {onepager_pdf}")
        logger.info(f"Created onePAGER pdf {onepager_pdf}")

        logger.info("Done.")
        return (True, "Success!")
    except Exception as e:
        f = io.StringIO()
        traceback.print_exc(file=f)
        msg = e
        msg = f"{str(msg)}\n {f.getvalue()}"
        hostname = socket.gethostname()
        msg = msg + "\n" + f"Error occurred on {hostname}\n"
        if gridfile is not None:
            msg = msg + "\n" + f"Error on file: {gridfile}\n"
        if eid is not None:
            msg = msg + "\n" + f"Error on event: {eid}\n"
        if pager_version is not None:
            msg = msg + "\n" + "Error on version: %i\n" % (pager_version)
        f.close()
        logger.critical(msg)
        logger.info("Sent error to email")
        return False
