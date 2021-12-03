# stdlib imports
import os.path
import smtplib
import mimetypes
from email import encoders
from email.message import Message
from email.mime.text import MIMEText
from email.mime.audio import MIMEAudio
from email.mime.base import MIMEBase
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
import email.utils

# local imports
from losspager.utils.exception import PagerException


def send_message(
    address, subject, text, sender, smtp_servers, attachment=None, bcc=None
):
    """
    Send a message to intended recipient with or without attachment.

    This method should determine the MIME type of the attachment and
    insert it into the message, along with the specified text.

    :param address: Email address of intended recipient.
    :param subject: Subject line text.
    :param text: Message text.
    :param attachment: File name of attachment.
    :param bcc: List of BCC recipients (None by default)
    :raises:
      PagerException when:
       - Attachment is not a valid file.
       - There is one of a number of errors connecting to email servers.
    """
    if attachment is not None and not os.path.isfile(attachment):
        raise PagerException(f"Attachment {attachment} is not a valid file")

    if not attachment:
        msg = MIMEText(text)
        msg["From"] = sender
        msg["To"] = address
        msg["Subject"] = subject
        msg["Date"] = email.utils.formatdate()
        if bcc is not None:
            bccstr = ", ".join(bcc)
            msg["Bcc"] = bccstr
        msgtxt = msg.as_string()
    else:
        msgtxt = __get_encoded_message(address, subject, text, attachment, bcc=bcc)

    messageSent = False
    errormsg = []
    # let's try all of the email servers we know about before
    # admitting defeat...
    for server in smtp_servers:
        # print 'Trying server %s' % (server)
        try:
            session = smtplib.SMTP(server)
            code, servername = session.helo()
            session.sendmail(sender, address, msgtxt)
            messageSent = True
            session.quit()
            break
        except smtplib.SMTPRecipientsRefused:
            errormsg.append({server: "Recipients refused"})
            continue
        except smtplib.SMTPHeloError:
            errormsg.append({server: "Server did not respond to hello"})
            continue
        except smtplib.SMTPSenderRefused:
            errormsg.append({server: "Server refused sender address"})
            continue
        except smtplib.SMTPDataError:
            errormsg.append({server: "Server responded with an unexpected error code"})
            continue
        except Exception:
            errormsg.append({server: "Connection to server failed (possible timeout)"})

    if not messageSent:
        errstr = (
            "The message to %s was not sent.  The server error messages are below:"
            % (address)
        )
        for errdict in errormsg:
            errstr = errstr + str(errdict)
        raise PagerException(str(errstr))

    print(f"Message sent to '{address}' via smtp server '{servername}'")
    if bcc is not None:
        print(f"Bcc: {','.join(bcc)}")


def __get_encoded_message(address, subject, text, sender, attachment, bcc=None):
    """
    Private method for encoding attachment into a MIME string.
    """
    outer = MIMEMultipart()
    outer["Subject"] = subject
    outer["To"] = address
    outer["From"] = sender
    outer["Date"] = email.utils.formatdate()
    if bcc is not None:
        outer["Bcc"] = ", ".join(bcc)

    # insert the text into the email as a MIMEText part...
    firstSubMsg = Message()
    firstSubMsg["Content-type"] = "text/plain"
    firstSubMsg["Content-transfer-encoding"] = "7bit"
    firstSubMsg.set_payload(text)
    outer.attach(firstSubMsg)

    # outer.preamble = 'You will not see this in a MIME-aware mail reader.\n'
    ctype, encoding = mimetypes.guess_type(attachment)
    msg = None
    if ctype is None or encoding is not None:
        # No guess could be made, or the file is encoded (compressed), so
        # use a generic bag-of-bits type.
        ctype = "application/octet-stream"
    maintype, subtype = ctype.split("/", 1)
    if maintype == "text":
        fp = open(attachment)
        # Note: we should handle calculating the charset
        msg = MIMEText(fp.read(), _subtype=subtype)
        fp.close()
    elif maintype == "image":
        fp = open(attachment, "rb")
        msg = MIMEImage(fp.read(), _subtype=subtype)
        fp.close()
    elif maintype == "audio":
        fp = open(attachment, "rb")
        msg = MIMEAudio(fp.read(), _subtype=subtype)
        fp.close()
    elif maintype == "application":
        fp = open(attachment, "rb")
        msg = MIMEApplication(fp.read(), _subtype=subtype)
        fp.close()
    else:
        fp = open(attachment, "rb")
        msg = MIMEBase(maintype, subtype)
        msg.set_payload(fp.read())
        fp.close()
        # Encode the payload using Base64
        encoders.encode_base64(msg)

    msg.add_header(
        "Content-Disposition", "attachment", filename=os.path.basename(attachment)
    )
    outer.attach(msg)

    return outer.as_string()
