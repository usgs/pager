#stdlib imports
import os
import copy
from datetime import datetime
from collections import OrderedDict

#third party imports
from impactutils.time.timeutils import LocalTime
from impactutils.textformat.text import pop_round_short
from impactutils.textformat.text import dec_to_roman
from impactutils.colors.cpalette import ColorPalette
from impactutils.comcat.query import ComCatInfo
from impactutils.io.cmd import get_command_output
import numpy as np

#local imports
from losspager.io.pagerdata import PagerData

LATEX_TO_PDF_BIN = 'pdflatex'

LATEX_SPECIAL_CHARACTERS = OrderedDict([('\\','\\textbackslash{}'),
                                        ('{','\{'),
                                        ('}','\}'),
                                        ('#','\#'),
                                        ('$','\$'),
                                        ('%','\%'),
                                        ('&','\&'),
                                        ('^','\\textasciicircum{}'),
                                        ('_','\_'),
                                        ('~','\textasciitilde{}')])

DEFAULT_PAGER_URL = 'http://earthquake.usgs.gov/data/pager/'

def texify(text):
    newtext = text
    for original,replacement in LATEX_SPECIAL_CHARACTERS.items():
        newtext = newtext.replace(original,replacement)
    return newtext

def create_onepager(pdata,version_dir, debug = False):
    """
    :param pdata:
      PagerData object.
    :param version_dir: 
      Path of event version directory.
    :param debug:
      bool for whether or not to add textpos boxes to onepager.
    """

    #---------------------------------------------------------------------------
    # Sort out some paths
    #---------------------------------------------------------------------------

    # Locaiton of this module
    mod_dir, dummy = os.path.split(__file__)

    # losspager package direcotry
    losspager_dir = os.path.join(mod_dir, '..')

    # Repository root directory
    root_dir = os.path.join(losspager_dir, '..')

    # Data directory
    data_dir = os.path.join(losspager_dir, 'data')

    # Onepager latex template file
    template_file = os.path.join(data_dir, 'onepager2.tex')

    #---------------------------------------------------------------------------
    # Read in pager data and latex template
    #---------------------------------------------------------------------------

    json_dir = os.path.join(version_dir, 'json')
    pdict = copy.deepcopy(pdata._pagerdict)
    edict = pdata.getEventInfo()
    
    with open(template_file, 'r') as f:
        template = f.read()

    #---------------------------------------------------------------------------
    # Fill in template values
    #---------------------------------------------------------------------------

    # Sort out origin time
    olat = edict['lat']
    olon = edict['lon']
    otime_utc = edict['time']
    date_utc = datetime.strptime(otime_utc, "%Y-%m-%d %H:%M:%S")
    
    date_local = pdata.local_time
    DoW = date_local.strftime('%a')
    otime_local = date_local.strftime('%H:%M:%S')
    otime_local = DoW + ' ' + otime_local
    template = template.replace("[ORIGTIME]", otime_utc)
    template = template.replace("[LOCALTIME]", otime_local)

    # Some paths
    template = template.replace("[VERSIONFOLDER]", version_dir)
    template = template.replace("[HOMEDIR]", root_dir)

    # Magnitude location string under USGS logo
    magloc = "M " + str(edict['mag']) + ", " + \
        edict['location']
    template = template.replace("[MAGLOC]", magloc)

    # Pager version
    ver = "Version " + str(pdict['pager']['version_number'])
    template = template.replace("[VERSION]", ver)
    template = template.replace("[VERSIONX]", "2.5")

    # Epicenter location
    lat = edict['lat']
    lon = edict['lon']
    dep = edict['depth']
    if lat > 0:
        hlat = "N"
    else:
        hlat = "S"
    if lon > 0:
        hlon = "E"
    else:
        hlon = "W"
    template = template.replace("[LAT]", str(abs(lat)))
    template = template.replace("[LON]", str(abs(lon)))
    template = template.replace("[HEMILAT]", str(hlat))
    template = template.replace("[HEMILON]", str(hlon))
    template = template.replace("[DEPTH]", str(dep))

    # Tsunami warning? --- need to fix to be a function of tsunamic flag
    if edict['tsunami']:
        template = template.replace("[TSUNAMI]", "FOR TSUNAMI INFORMATION, SEE: tsunami.gov")
    else:
        template = template.replace("[TSUNAMI]", "")

    if pdata.isScenario():
        elapse = ''
    else:
        elapse = "Created: " + pdict['pager']['elapsed_time'] + " after earthquake"
    template = template.replace("[ELAPSED]", elapse)
    template = template.replace("[IMPACT1]", texify(pdict['comments']['impact1']))
    template = template.replace("[IMPACT2]", texify(pdict['comments']['impact2']))
    template = template.replace("[STRUCTCOMMENT]", texify(pdict['comments']['struct_comment']))

    # Fill in exposure values
    mmi = np.array(pdict['population_exposure']['mmi'])
    exp = np.array(pdict['population_exposure']['aggregated_exposure'])
    cum_exp = np.cumsum(exp)
    not_covered = cum_exp == 0
    template = template.replace("[MMI]", "MMI")
    if not_covered[0] == True:
        mmi1 = '--*'
    else:
        mmi1 = pop_round_short(exp[mmi == 1][0])
    template = template.replace("[MMI1]", mmi1)
    if not_covered[2] == True:
        mmi23 = '--*'
    else:
        mmi23 = pop_round_short(np.sum(exp[(mmi == 2) | (mmi == 3)]))
    template = template.replace("[MMI2-3]", mmi23)
    if not_covered[3] == True:
        mmi4 = '--*'
    else:
        mmi4 = pop_round_short(exp[mmi == 4][0])
    template = template.replace("[MMI4]", mmi4)
    if not_covered[4] == True:
        mmi5 = '--*'
    else:
        mmi5 = pop_round_short(exp[mmi == 5][0])
    template = template.replace("[MMI5]", mmi5)
    template = template.replace("[MMI6]", pop_round_short(exp[mmi == 6][0]))
    template = template.replace("[MMI7]", pop_round_short(exp[mmi == 7][0]))
    template = template.replace("[MMI8]", pop_round_short(exp[mmi == 8][0]))
    template = template.replace("[MMI9]", pop_round_short(exp[mmi == 9][0]))
    template = template.replace("[MMI10]", pop_round_short(exp[mmi == 10][0]))

    # MMI color pal
    pal = ColorPalette.fromPreset('mmi')

    # Historical table
    htab = pdata.getHistoricalTable()
    if htab[0] is None:
        # use pdata.getHistoricalComment()
        htex = pdata.getHistoricalComment()
    else:
        # build latex table
        htex = """
\\begin{tabularx}{7.25cm}{lrc*{1}{>{\\centering\\arraybackslash}X}r}
\hline
\\textbf{Date} &\\textbf{Dist.}&\\textbf{Mag.}&\\textbf{Max}    &\\textbf{Shaking}\\\\
\\textbf{(UTC)}&\\textbf{(km)} &              &\\textbf{MMI(\#)}&\\textbf{Deaths} \\\\
\hline
[TABLEDATA]
\hline
\multicolumn{5}{p{7.2cm}}{\\raggedright \\footnotesize [COMMENT]}
\end{tabularx}"""
        comment = pdata._pagerdict['comments']['secondary_comment']
        htex = htex.replace("[COMMENT]", texify(comment))
        tabledata = ""
        nrows = len(htab)
        for i in range(nrows):
            date = htab[i]['Time'].split()[0]
            dist = str(int(htab[i]['Distance']))
            mag = str(htab[i]['Magnitude'])
            mmi = dec_to_roman(np.round(htab[i]['MaxMMI'], 0))
            col = pal.getDataColor(htab[i]['MaxMMI'])
            texcol = "%s,%s,%s" %(col[0], col[1], col[2])
            nmmi = pop_round_short(htab[i]['NumMaxMMI'])
            mmicell = '%s(%s)' %(mmi, nmmi)
            shakedeath = htab[i]['ShakingDeaths']
            if np.isnan(shakedeath):
                death = "--"
            else:
                death = pop_round_short(shakedeath)
            row = '%s & %s & %s & \cellcolor[rgb]{%s} %s & %s \\\\ '\
                  '\n' %(date, dist, mag, texcol, mmicell, death)
            tabledata = tabledata + row
        htex = htex.replace("[TABLEDATA]", tabledata)
    template = template.replace("[HISTORICAL_BLOCK]", htex)

    # City table
    ctex = """
\\begin{tabularx}{7.25cm}{lXr}
\hline
\\textbf{MMI} & \\textbf{City} & \\textbf{Population}  \\\\
\hline
[TABLEDATA]
\hline
\end{tabularx}"""
    ctab = pdata.getCityTable()
    nrows = len(ctab.index)
    tabledata = ""
    for i in range(nrows):
        mmi = dec_to_roman(np.round(ctab['mmi'].iloc[i], 0))
        city = ctab['name'].iloc[i]
        pop = pop_round_short(ctab['pop'].iloc[i])
        col = pal.getDataColor(ctab['mmi'].iloc[i])
        texcol = "%s,%s,%s" %(col[0], col[1], col[2])
        if ctab['on_map'].iloc[i] == 1:
            row = '\\rowcolor[rgb]{%s}\\textbf{%s} & \\textbf{%s} & '\
                  '\\textbf{%s}\\\\ \n' %(texcol, mmi, city, pop)
        else:
            row = '\\rowcolor[rgb]{%s}%s & %s & '\
                  '%s\\\\ \n' %(texcol, mmi, city, pop)
        tabledata = tabledata + row
    ctex = ctex.replace("[TABLEDATA]", tabledata)
    template = template.replace("[CITYTABLE]", ctex)


    eventid = edict['eventid']

    #query ComCat for information about this event
    #fill in the url, if we can find it
    try:
        ccinfo = ComCatInfo(eventid)
        eventid,allids = ccinfo.getAssociatedIds()
        event_url = ccinfo.getURL()+'#pager'
    except:
        event_url = DEFAULT_PAGER_URL

    eventid = "Event ID: " + eventid
    template = template.replace("[EVENTID]", texify(eventid))
    template = template.replace("[EVENTURL]", texify(event_url))

    # Write latex file
    tex_output = os.path.join(version_dir, 'onepager.tex')
    with open(tex_output, 'w') as f:
        f.write(template)

    pdf_output = os.path.join(version_dir, 'onepager.pdf')
    stderr = ''
    try:
        cwd = os.getcwd()
        os.chdir(version_dir)
        cmd = '%s -interaction nonstopmode --output-directory %s %s' % (LATEX_TO_PDF_BIN,version_dir,tex_output)
        print('Running %s...' % cmd)
        res,stdout,stderr = get_command_output(cmd)
        os.chdir(cwd)
        if not res:
            return (None,stderr)
        else:
            if os.path.isfile(pdf_output):
                return (pdf_output,stderr)
            else:
                pass
    except Exception as e:
        pass
    finally:
        os.chdir(cwd)
    return (None,stderr)
