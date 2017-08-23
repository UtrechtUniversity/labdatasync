# import subprocess

# telnetcommand = """(
# echo "HELO smpt.uu.nl"
# sleep 3
# echo "MAIL from: lenovo1@soliscom.uu.nl"
# sleep 3
# echo "RCPT TO: j.c.vanelst@uu.nl"
# sleep 3
# echo "DATA"
# sleep 3
# echo "hallo daar"
# sleep 3
# echo "QUIT"
# sleep 2
# ) | telnet smpt.uu.nl 25"""

# do = subprocess.Popen(telnetcommand, shell=True)
# try:
    # outs, errs = do.communicate(timeout=30)
    # print (outs, errs)
	
# except:
    # do.kill()
    # outs, errs = do.communicate()
    # print ('2', outs, errs)
	
import smtplib

SERVER = "smtp.uu.nl"

FROM = "sender@example.com"
TO = ["j.c.vanelst@uu.nl"] # must be a list

SUBJECT = "Hello!"

TEXT = "This message was sent with Python's smtplib."

# Prepare actual message

message = """\
From: %s
To: %s
Subject: %s

%s
""" % (FROM, ", ".join(TO), SUBJECT, TEXT)

# Send the mail

server = smtplib.SMTP(SERVER)
server.sendmail(FROM, TO, message)
server.quit()