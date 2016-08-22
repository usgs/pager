#!/usr/bin/python

#stdlib imports
import re
import sys
import random
from math import floor,ceil,log10

# these two lists serves as building blocks to construct any roman numeral
# just like coin denominations.
# 1000->"M", 900->"CM", 500->"D"...keep on going 
decimalDens=[1000,900,500,400,100,90,50,40,10,9,5,4,1]
romanDens=["M","CM","D","CD","C","XC","L","XL","X","IX","V","IV","I"]
def dec_to_roman(dec):
    """Return roman numeral version of Arabic integer numeral (limit 4000).

    Example::
      decToRoman(11) => 'XI'
      decToRoman(1025) => 'MXXV'
      
    :param dec: 
      Integer Arabic numeral.
    :returns: 
      Roman numeral equivalent of input, as string.
    :raises ValueError: 
      When input is negative or greater or equal to 4000.
    """		
    if dec <=0:
        raise ValueError("Input value must be positive")
        # to avoid MMMM
    elif dec>=4000:  
        raise ValueError("Input value must be lower than MMMM(4000)")
    
    return _dec_to_roman(dec,"",decimalDens,romanDens)

def _dec_to_roman(num,s,decs,romans):
    """
    convert a Decimal number to Roman numeral recursively
    :param num: 
      the decimal number
    :param s: 
      the roman numerial string
    :param decs: 
      current list of decimal denomination
    :param romans: 
      current list of roman denomination
    :returns: 
      Roman numeral equivalent of num, as string.
    """
    if decs:
        if (num < decs[0]):
            # deal with the rest denomination
            return _dec_to_roman(num,s,decs[1:],romans[1:])		  
        else:
            # deduce this denomation till num<desc[0]
            return _dec_to_roman(num-decs[0],s+romans[0],decs,romans)	  
    else:
        # we run out of denomination, we are done 
        return s

def set_num_precision(number,precision,mode='int'):
    """
    Return the input number with N digits of precision
    :param number:  
      Input value
    :param precision: 
      Number of digits of desired precision
    :returns:  
      Input value with 'precision' digits of precision.
    """
    ndigits = len(str(int(floor(number))))
    value = round(10.0**(precision-1) * number/(10.0**(ndigits-1))) / 10.0**(precision-1)
    value = value * 10.0**(ndigits-1)
    if mode == 'int':
        return int(value)
    else:
        return value

def pop_round(value):
    """
    Round population value to nearest 1000, return as human readable string with commas.
    
    Example::
      print popRound(9184) => '10,000'

    :param value: 
      Population value to be rounded.
    :returns: 
      "Commified" string form of value, rounded to nearest 1000.
    """
    return commify(round_to_nearest(value))

def dollar_round(value,digits=2,mode='short'):
    """Return an abbreviated dollar value.
    
    :param value: 
      Input integer dollar value (i.e., 1000000)
    :keyword mode: 
      'short' or 'long' (default 'short')
    :param digits: 
      Number of significant digits (default 2).
    :returns: 
      Rounded string version of dollar amount (i.e., $1.0B or $1.0 billion
    """
    if value < 1e3:
        return '$'+commify(set_num_precision(value,digits))
    suffixdict = {'K':1e3,'M':1e6,'B':1e9}
    if mode == 'short':
        if value >= suffixdict['K'] and value < suffixdict['M']:
            return '$%sK' % set_num_precision(value/1e3,digits,mode='float')
        if value >= suffixdict['M'] and value < suffixdict['B']:
            return '$%sM' % set_num_precision(value/1e6,digits,mode='float')
        else:
            return '$%sB' % set_num_precision(value/1e9,digits,mode='float')
    else:
        if value >= suffixdict['K'] and value < suffixdict['M']:
            return '$%s thousand' % set_num_precision(value/1e3,digits,mode='float')
        if value > suffixdict['M'] and value < suffixdict['B']:
            return '$%s million' % set_num_precision(value/1e6,digits,mode='float')
        else:
            return '$%s billion' % set_num_precision(value/1e9,digits,mode='float')

def pop_round_short(value,usemillion=False):
    """Return an abbreviated population value (i.e., '1,024k' for 1,024,125, '99k' for 99,125, '9k' for 9,125)
    
    :param value: Population value to be shortened.
    :param usemillion: 
      If True, values greater than 1 million will be appended with 'm'.  Default always appends 'k'.
    :returns: 
      String population value with 'k' or 'm' appended (or nothing if 0)
    """
    if value < 1000:
        return str(int(value))
    suffixdict = {'k':1000,'m':1000000}
    if value >= suffixdict['m'] and usemillion:
        suffix = 'm'
    else:
        suffix = 'k'

    roundValue = suffixdict[suffix]
    roundnum = round_to_nearest(value)//roundValue
    if roundnum == 0:
        return str(roundnum)
    else:
        return commify(roundnum)+suffix

def round_to_nearest(value,round_value=1000):
    """Return the value, rounded to nearest round_value (defaults to 1000).
    
    :param value: 
      Value to be rounded.
    :param round_value: 
      Number to which the value should be rounded.
    :returns:
      Value rounded to nearest desired integer.
    """
    if round_value < 1:
        ds = str(round_value)
        nd = len(ds) - (ds.find('.')+1)
        value = value * 10**nd
        round_value = round_value * 10**nd
        value = int(round(float(value)/round_value)*round_value)
        value = float(value) / 10**nd
    else:
        value = int(round(float(value)/round_value)*round_value)
    
    return value

def floor_to_nearest(value,floor_value=1000):
    """Return the value, floored to nearest floor_value (defaults to 1000).
    
    :param value: 
      Value to be floored.
    :param floor_value: 
      Number to which the value should be floored.
    :returns:
      Floored value.
    """
    if floor_value < 1:
        ds = str(floor_value)
        nd = len(ds) - (ds.find('.')+1)
        value = value * 10**nd
        floor_value = floor_value * 10**nd
        value = int(floor(float(value)/floor_value)*floor_value)
        value = float(value) / 10**nd
    else:
        value = int(floor(float(value)/floor_value)*floor_value)
    return value

def ceil_to_nearest(value,ceil_value=1000):
    """Return the value, ceiled to nearest ceil_value (defaults to 1000).
    
    :param value: 
      Value to be ceiled.
    :param ceil_value: 
      Number to which the value should be ceiled.
    :returns:
      Ceiled value.
    """
    if ceil_value < 1:
        ds = str(ceil_value)
        nd = len(ds) - (ds.find('.')+1)
        value = value * 10**nd
        ceil_value = ceil_value * 10**nd
        value = int(ceil(float(value)/ceil_value)*ceil_value)
        value = float(value) / 10**nd
    else:
        value = int(ceil(float(value)/ceil_value)*ceil_value)
    return value
    
def commify(num, separator=','):
    """Return a string representing the number num with separator inserted for every power of 1000.
    
    commify(1234567) -> '1,234,567'
    
    :param num: 
      Number to be formatted.
    :param separator: 
      Separator to be used.
    :returns: 
      "Commified" string.
    """
    regex = re.compile(r'^(-?\d+)(\d{3})')
    num = str(num)  # just in case we were passed a numeric value
    more_to_do = 1
    while more_to_do:
        (num, more_to_do) = regex.subn(r'\1%s\2' % separator,num)
    return num
