#!/usr/bin/env python

# stdlib imports
import os.path

# third party imports
import pandas as pd


class PagerRegions(object):
    def __init__(self):
        """Class which contains groupings of country codes into PAGER vulnerability regions 1-6,
        where region 1 is the least vulnerable, and region 6 is the most vulnerable.  It also contains
        a vulnerability comment for each region.

        The data for this class lives in the PAGER code repository.
        """
        homedir = os.path.dirname(os.path.abspath(__file__))  # where is this script?
        excelfile = os.path.abspath(
            os.path.join(homedir, "..", "data", "pager_regions.xlsx")
        )
        self._loadFromExcel(excelfile)

    def _loadFromExcel(self, excelfile):
        """Load data from an excel spreadsheet into the regions and comments data structures.

        :param excelfile:
          Excel file containing 6 sheets called 'Region1', 'Region2', ..., 'Region6'.
          Each sheet should contain columns: 'codes','names','comment'.  The 'codes' column
          should contain the two letter country codes of all countries that belong to the given region.
          The 'names' column should contain the short country names - this is only used for human readability.
          The 'comment' column should have a string in the first row under the header containing a description
          of building vulnerability in that region.
        """
        self._region1 = pd.read_excel(excelfile, sheet_name="Region1")["codes"].tolist()
        self._region2 = pd.read_excel(excelfile, sheet_name="Region2")["codes"].tolist()
        self._region3 = pd.read_excel(excelfile, sheet_name="Region3")["codes"].tolist()
        self._region4 = pd.read_excel(excelfile, sheet_name="Region4")["codes"].tolist()
        self._region5 = pd.read_excel(excelfile, sheet_name="Region5")["codes"].tolist()
        self._region6 = pd.read_excel(excelfile, sheet_name="Region6")["codes"].tolist()
        self._comments = {
            1: str(pd.read_excel(excelfile, sheet_name="Region1")["comment"][0]),
            2: str(pd.read_excel(excelfile, sheet_name="Region2")["comment"][0]),
            3: str(pd.read_excel(excelfile, sheet_name="Region3")["comment"][0]),
            4: str(pd.read_excel(excelfile, sheet_name="Region4")["comment"][0]),
            5: str(pd.read_excel(excelfile, sheet_name="Region5")["comment"][0]),
            6: str(pd.read_excel(excelfile, sheet_name="Region6")["comment"][0]),
        }

    def getRegion(self, ccode):
        """Get the PAGER region (1-6) corresponding to input country code.

        :param ccode:
          Two letter ISO country code.
        :returns:
          Integer PAGER region 1-6.
        """
        if ccode in self._region1:
            return 1
        if ccode in self._region2:
            return 2
        if ccode in self._region3:
            return 3
        if ccode in self._region4:
            return 4
        if ccode in self._region5:
            return 5
        if ccode in self._region6:
            return 6
        return 0

    def getComment(self, region):
        """Get the vulnerability comment associated with a given PAGER region.

        :param region:
          Integer PAGER region 1-6.
        :returns:
          String describing building vulnerability in that region, or ''.
        """
        if region in self._comments:
            return self._comments[region]
        return ""
