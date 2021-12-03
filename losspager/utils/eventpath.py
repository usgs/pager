# stdlib imports
import os.path

# third-party imports
from impactutils.comcat.query import ComCatInfo


def get_event_folder(eventid, outfolder):
    eventfolder = os.path.join(outfolder, eventid)
    if os.path.isdir(eventfolder):
        return eventfolder
    else:
        try:
            ccinfo = ComCatInfo(eventid)
            # try to get all the possible event ids before failing
            authid, allids = ccinfo.getAssociatedIds()
            allids.append(authid)
            for eid in allids:
                eventfolder = os.path.join(outfolder, eid)
                if os.path.isdir(eventfolder):
                    return eventfolder
        except:
            pass
    if not os.path.isdir(eventfolder):
        os.makedirs(eventfolder)
    return eventfolder
