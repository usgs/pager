#!/usr/bin/env python

# stdlib imports
import os.path
import numpy as np
import pandas as pd
import tempfile
import shutil

from mapio.shake import ShakeGrid

# local imports
from losspager.io.hazus import HazusInfo


def test_map():
    tdir = tempfile.mkdtemp()
    try:
        mapname = os.path.join(tdir, 'test_map.pdf')
        # where is this script?
        homedir = os.path.dirname(os.path.abspath(__file__))
        datadir = os.path.join(homedir, '..', 'data', 'nyc')
        shakefile = os.path.join(datadir, 'm5.8.nyc.grid.xml')
        shakegrid = ShakeGrid.load(shakefile)

        countyfile = os.path.join(datadir, 'county_results.txt')
        tractfile = os.path.join(datadir, 'tract_results.txt')
        damage_occupancy = os.path.join(datadir, 'building_damage_occup.txt')
        hazinfo = HazusInfo(tdir, tractfile, countyfile, damage_occupancy)
        green, yellow, red = hazinfo.createTaggingTables()

        green_table = '\\begin{tabularx}{3.4cm}{lr}\n& \\\\\n\\multicolumn{2}{c}{\\textbf{INSPECTED}} \\\\\n\\textbf{Occupancy} & \\textbf{\\# of tags}  \\\\\nResidential & 15k \\\\\nSingle Family & 20k \\\\\nCommercial & 4k \\\\\nIndustrial & 900 \\\\\nEducation & 158 \\\\\nAgriculture & 94 \\\\\nGovernment & 77 \\\\\n\\end{tabularx}'

        yellow_table = '\\begin{tabularx}{3.4cm}{lr}\n& \\\\\n\\multicolumn{2}{c}{\\textbf{RESTRICTED USE}} \\\\\n\\textbf{Occupancy} & \\textbf{\\# of tags}  \\\\\nResidential & 516 \\\\\nSingle Family & 501 \\\\\nCommercial & 161 \\\\\nIndustrial & 30 \\\\\nEducation & 5 \\\\\nAgriculture & 2 \\\\\nGovernment & 2 \\\\\n\\end{tabularx}'

        red_table = '\\begin{tabularx}{3.4cm}{lr}\n& \\\\\n\\multicolumn{2}{c}{\\textbf{UNSAFE}} \\\\\n\\textbf{Occupancy} & \\textbf{\\# of tags}  \\\\\nResidential & 50 \\\\\nSingle Family & 51 \\\\\nCommercial & 12 \\\\\nIndustrial & 1 \\\\\nEducation & 0 \\\\\nAgriculture & 0 \\\\\nGovernment & 0 \\\\\n\\end{tabularx}'

        assert green == green_table
        assert yellow == yellow_table
        assert red == red_table

        print('Green:')
        print(green)
        print()
        print('Yellow:')
        print(yellow)
        print()
        print('Red:')
        print(red)

        loss = hazinfo.createEconTable()
        loss_table = '\\begin{tabularx}{\\barwidth}{lc*{1}{>{\\raggedleft\\arraybackslash}X}}\n\\hline\n\\textbf{County} & \\textbf{State} & \\textbf{Total (\\textdollar M)} \\\\\n\\hline\nKings & NY & 3,183 \\\\\nRichmond & NY & 493 \\\\\nNew York & NY & 272 \\\\\nQueens & NY & 202 \\\\\nHudson & NJ & 132 \\\\\nUnion & NJ & 93 \\\\\nMonmouth & NJ & 74 \\\\\n\\multicolumn{2}{l}{\\textbf{Total (19 counties)}} & \\multicolumn{1}{>{\\raggedleft}X}{\\textbf{4,643}} \\\\\n\\hline\n\\end{tabularx}'
        assert loss == loss_table
        print()
        print('Econ Losses:')
        print(loss)

        injury = hazinfo.createInjuryTable()
        injury_table = '\\begin{tabularx}{\\barwidth}{lc*{2}{>{\\raggedleft\\arraybackslash}X}}\n\\hline\n\\textbf{County} & \\textbf{State} & \\textbf{Population} & \\textbf{Total NFI} \\\\\n\\hline\nKings & NY & 2,505k & 302 \\\\\nRichmond & NY & 469k & 36 \\\\\nNew York & NY & 1,586k & 15 \\\\\nQueens & NY & 2,231k & 32 \\\\\nHudson & NJ & 634k & 12 \\\\\nUnion & NJ & 536k & 10 \\\\\nMonmouth & NJ & 630k & 7 \\\\\n\\multicolumn{2}{l}{\\textbf{Total (19 counties)}} & \\multicolumn{1}{>{\\raggedleft}X}{\\textbf{18,517k}} & \\multicolumn{1}{>{\\raggedleft}X}{\\textbf{447}} \\\\\n\\hline\n\\end{tabularx}'
        assert injury == injury_table
        print()
        print('Injuries:')
        print(injury)

        shelter = hazinfo.createShelterTable()
        shelter_table = '\\begin{tabularx}{\\barwidth}{lc*{3}{>{\\raggedleft\\arraybackslash}X}}\n\\hline\n\\               &                 & \\textbf{Total}  & \\textbf{Displ}  & \\textbf{People}  \\\\\n\\               &                 & \\textbf{House-} & \\textbf{House-} & \\textbf{Needing} \\\\\n\\textbf{County} & \\textbf{State} & \\textbf{holds}  & \\textbf{holds}  & \\textbf{Shelter} \\\\\n\\hline\nKings & NY & 917k & 2k & 2k \\\\\nRichmond & NY & 166k & 162 & 106 \\\\\nNew York & NY & 764k & 102 & 52 \\\\\nQueens & NY & 780k & 146 & 106 \\\\\nHudson & NJ & 246k & 72 & 46 \\\\\nUnion & NJ & 188k & 44 & 36 \\\\\nMonmouth & NJ & 234k & 18 & 10 \\\\\n\\multicolumn{2}{l}{\\textbf{Total (19 counties)}} & \\multicolumn{1}{>{\\raggedleft}X}{\\textbf{6,794k}} & \\multicolumn{1}{>{\\raggedleft}X}{\\textbf{3k}} & \\multicolumn{1}{>{\\raggedleft}X}{\\textbf{2k}} \\\\\n\\hline\n\\end{tabularx}'
        assert shelter == shelter_table

        print()
        print('Shelter Needs:')
        print(loss)

        debris = hazinfo.createDebrisTable()
        debris_table = '\\begin{tabularx}{\\barwidth}{l*{1}{>{\\raggedleft\\arraybackslash}X}}\n\\hline\n\\                 & \\textbf{Tons}      \\\\\n\\textbf{Category} & \\textbf{(millions)} \\\\\n\\hline\nBrick / Wood & 0.449 \\\\\nReinforced Concrete / Steel & 0.149 \\\\\n\\textbf{Total} & \\textbf{0.598} \\\n&  \\\\\n&  \\\\\n\\textbf{Truck Loads (@25 tons/truck)} & \\textbf{23,908} \\\n\\end{tabularx}'
        assert debris == debris_table

        print()
        print('Debris:')
        print(debris)

        model_config = {}
        model_config['states'] = os.path.join(datadir, 'nyc_states.shp')
        model_config['counties'] = os.path.join(datadir, 'nyc_counties.shp')
        model_config['tracts'] = os.path.join(datadir, 'nyc_tracts.shp')
        model_config['ocean_vectors'] = os.path.join(datadir, 'nyc_oceans.shp')
        hazinfo.drawHazusMap(shakegrid, mapname, model_config)
        assert os.path.isfile(mapname)

    except Exception as e:
        assert 1 == 2
    finally:
        shutil.rmtree(tdir)


if __name__ == '__main__':
    test_map()
