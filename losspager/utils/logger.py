#!/usr/bin/python

#stdlib imports
import logging
from logging.handlers import SMTPHandler
import sys
import os
import socket
from datetime import datetime
import smtplib

class NullHandler(logging.Handler):
    def emit(self, record):
        pass

class OutStream:
    """
    Sends text to a logging object as INFO.
    """
    def __init__(self,logger):
        """
        Create an OutStream with an instance of a logger from the python logging module.

        :param logger: 
          Result of calling logging.getLogger('LogName')
        """
        self.Logger = logger

    def write(self,text):
        """
        Write output to Logger instance as INFO.

        :param text:
          Text to write to Logger instance.
        """
        if text and not text.isspace():
            self.Logger.info(text)
            
    def flush(self):
        """Method to complete the stream interface.  Does nothing.

        """
        pass

class ErrStream:
    """
    Sends text to a logging object as ERROR.
    """
    def __init__(self,logger):
        """
        Create an ErrStream with an instance of a logger from the python logging module.

        :param logger:
          Result of calling logging.getLogger('LogName')
        """
        self.Logger = logger
        
    def write(self,text):
        """
        Write output to Logger instance as ERROR.

        :param text:
          Text to write to Logger instance.
        """
        if text and not text.isspace():
            self.Logger.error(text)

    def flush(self):
        """Method to complete the stream interface.  Does nothing.

        """
        pass

class PagerLogger:
    """
    Wrapper around Python logging module.

    This class simplifies some of the configuration for logging 
    PAGER errors.  Simple usage::
      from util.logger import PagerLogger
      plog = PagerLogger(logfile)
      plog.addEmailHandler(['dev@developer.gov'])
      plogger = plog.getLogger()
      try:
          print('This should show up as information!')
          sys.stderr.write('This should show up as an error!')
          raise Exception,"This should show up as critical (and generate an email)!"
      except Exception,msg:
          plogger.critical(msg)
    """
    Subject = 'PAGER Error'
    EmailLogLevel = logging.CRITICAL
    OldOut = None
    OldErr = None
    isOnline = False
    EventLogHandler = None
    MailHandler = None
    PagerLogHandler = None
    def __init__(self,pagerlogfile,from_address=None,mail_hosts=None,redirect=True):
        """
        Create a PagerLogger instance, and begin logging to the PAGER (not event) log file.

        Initially, without calling any other functions, this will log results only to this file.
        When the version folder is created, users should call addEventFileHandler(), which will turn off
        the general pager log file.

        :param pagerlogfile: 
          Name of local file where logging information should be written.
        :param from_address:
          Email address where error messages will come from.
        :param mail_hosts:
          String indicating the hostname or IP address of a valid SMTP server.
        :param redirect:
          Boolean indicating whether or not stdout and stderr should be redirected to
          log file.  Wise to turn off when debugging.
        """
        #h = NullHandler()
        logger = logging.getLogger('PagerLog')
        #logger.addHandler(h)
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        #formatter = logging.Formatter(fmt='${levelname} ${asctime} ${message}')
        self.PagerLogHandler = logging.FileHandler(pagerlogfile)
        self.PagerLogHandler.setFormatter(formatter)
        logger.addHandler(self.PagerLogHandler)
        
        logger.setLevel(logging.INFO)
        self.Logger = logger
        self.Formatter = formatter
        if redirect:
            self.enableRedirect()

        #check to verify that we are connected to a network.  If not, email handler
        #can't be added later
        self.isOnline = True
        if socket.gethostbyname(socket.gethostname()) == '127.0.0.1':
            self.isOnline = False
            
        self.FromAddress = from_address
        self.MailHosts = mail_hosts

    def scream(self,msg):
        """
        Send out a CRITICAL level warning message, which will go through the email handler if it is turned on.

        :param msg: 
          Text message to be logged as CRITICAL.
        """
        self.disableRedirect()
        self.Logger.critical(msg)
        self.enableRedirect()
        

    def enableRedirect(self):
        """
        Send stdout/stderr to OutStream object.
        """
        
        self.OldOut = sys.stdout
        self.OldErr = sys.stderr
        sys.stdout = OutStream(self.Logger)
        sys.stderr = OutStream(self.Logger)

    def disableRedirect(self):
        """
        Send stdout/stderr back to original output streams.
        """
        if self.OldOut is None:
            return
        sys.stdout = self.OldOut
        sys.stderr = self.OldErr
        self.OldOut = None
        self.OldErr = None

    def switchToEventFileHandler(self,eventlogfile):
        """
        Add event log to logger.  Also removes general pager log from the logger object.
        :param eventlogfile: 
          Desired full path to event log file.
        """
        #add the event file handler 
        self.EventLogHandler = logging.FileHandler(eventlogfile)
        self.EventLogHandler.setFormatter(self.Formatter)
        self.Logger.addHandler(self.EventLogHandler)

        #remove the pager log handler
        self.Logger.removeHandler(self.PagerLogHandler)

    def addEmailHandler(self,emails):
        """
        Add an email handler.

        Important notes: The email handler uses the following class variables:
          - FromAddress - Emails show up as being from this address.
          - MailHosts - Mails are processed through one of these mail servers.
          - Subject - Emails have this subject line.
          - LogLevel - (IMPORTANT!) Only log messages with this log level and above 
            will be sent by email.
          
        Use this email functionality with caution.

        :param emails: 
          List of email addresses that should receive error notifications.
        """
        if not self.isOnline:
            print('Could not add mail handler as this system is not networked.')
            return
        self.MailHandler = None
        print('Creating SMTP handler with %s,%s,%s,%s' % (self.MailHosts,self.FromAddress,emails,self.Subject))
        #we supply a list of smtp hosts, just in case some of them are off-line... here we find the first 
        #one that seems to be responsive.
        try:
            subject = self.Subject + ': %s' % datetime.utcnow().strftime('%b %d %Y %H:%M:%S')
            smtphost = None
            for host in self.MailHosts:
                with smtplib.SMTP(host) as smtp:
                    #if I can connect, and send this noop message, then this server
                    #should be good to go.  Various sources indicate that calling noop() too many
                    #times can be interpreted as a form of DOS attack, so use with caution.
                    res = smtp.noop() 
                    smtp.close()
                    if res[0] == 250:
                        smtphost = host
                        break
            if smtphost is None:
                raise PagerException('Could not connect to any mail hosts: %s' % str(self.MailHosts))

            self.MailHandler = SMTPHandler(smtphost,self.FromAddress,emails,subject)
            self.MailHandler.setLevel(self.EmailLogLevel)
            self.MailHandler.setFormatter(self.Formatter)
            self.Logger.addHandler(self.MailHandler)
        except:
            msg = ''
            print('Could not add mail handler (%s).' % (msg))
        
    def stopLogging(self):
        """
        Stop logging, return stdout and stderr to normal state.
        """
        if self.PagerLogHandler:
            self.Logger.removeHandler(self.PagerLogHandler)
        if self.MailHandler:
            self.Logger.removeHandler(self.MailHandler)
        if self.EventLogHandler:
            self.Logger.removeHandler(self.EventLogHandler)
        sys.stdout = self.OldOut
        sys.stderr = self.OldErr
    
    def getLogger(self):
        """
        Return the logger instance.
        """
        return self.Logger
