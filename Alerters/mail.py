# coding=utf-8
import smtplib
try:
    from email.MIMEMultipart import MIMEMultipart
    from email.MIMEText import MIMEText
except ImportError:
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText

from .alerter import Alerter


class EMailAlerter(Alerter):
    """Send email alerts using SMTP to a mail server."""

    def __init__(self, config_options):
        Alerter.__init__(self, config_options)
        self.mail_host = Alerter.get_config_option(
            config_options,
            'host',
            required=True,
            allow_empty=False
        )
        self.from_addr = Alerter.get_config_option(
            config_options,
            'from',
            required=True,
            allow_empty=False
        )
        self.to_addr = Alerter.get_config_option(
            config_options,
            'to',
            required=True,
            allow_empty=False
        )
        self.mail_port = Alerter.get_config_option(
            config_options,
            'port',
            required_type='int',
            default=25
        )
        self.username = Alerter.get_config_option(
            config_options,
            'username'
        )
        self.password = Alerter.get_config_option(
            config_options,
            'password'
        )
        self.ssl = Alerter.get_config_option(
            config_options,
            'ssl',
            allowed_values=['starttls', 'yes']
        )
        if self.ssl == 'yes':
            print('Warning: ssl=yes for email alerter is untested')

        self.support_catchup = True

    def send_alert(self, name, monitor):
        """Send the email."""

        type = self.should_alert(monitor)
        (days, hours, minutes, seconds) = self.get_downtime(monitor)

        if monitor.is_remote():
            host = " on %s " % monitor.running_on
        else:
            host = " on host %s" % self.hostname

        message = MIMEMultipart()
        message['From'] = self.from_addr
        message['To'] = self.to_addr

        if type == "":
            return
        elif type == "failure":
            message['Subject'] = "[%s] Monitor %s Failed!" % (self.hostname, name)
            body = """Monitor %s%s has failed.
            Failed at: %s
            Downtime: %d+%02d:%02d:%02d
            Virtual failure count: %d
            Additional info: %s
            Description: %s""" % (
                name,
                host,
                self.format_datetime(monitor.first_failure_time()),
                days, hours, minutes, seconds,
                monitor.virtual_fail_count(),
                monitor.get_result(),
                monitor.describe())
            try:
                if monitor.recover_info != "":
                    body += "\nRecovery info: %s" % monitor.recover_info
            except AttributeError:
                body += "\nNo recovery info available"

        elif type == "success":
            message['Subject'] = "[%s] Monitor %s succeeded" % (self.hostname, name)
            body = "Monitor %s%s is back up.\nOriginally failed at: %s\nDowntime: %d+%02d:%02d:%02d\nDescription: %s" % (name, host, self.format_datetime(monitor.first_failure_time()), days, hours, minutes, seconds, monitor.describe())

        elif type == "catchup":
            message['Subject'] = "[%s] Monitor %s failed earlier!" % (self.from_addr, self.to_addr, self.hostname, name)
            body = "Monitor %s%s failed earlier while this alerter was out of hours.\nFailed at: %s\nVirtual failure count: %d\nAdditional info: %s\nDescription: %s" % (name, host, self.format_datetime(monitor.first_failure_time()), monitor.virtual_fail_count(), monitor.get_result(), monitor.describe())

        else:
            print("Unknown alert type %s" % type)
            return

        message.attach(MIMEText(body, 'plain'))

        if not self.dry_run:
            try:
                if self.ssl is None or self.ssl == 'starttls':
                    server = smtplib.SMTP(self.mail_host, self.mail_port)
                elif self.ssl == 'yes':
                    server = smtplib.SMTP_SSL(self.mail_host, self.mail_port)

                if self.ssl == 'starttls':
                    server.starttls()

                if self.username is not None:
                    server.login(self.username, self.password)
                server.sendmail(self.from_addr, self.to_addr, message.as_string())
                server.quit()
            except Exception as e:
                print("Couldn't send mail: %s" % e)
                self.available = False
        else:
            print("dry_run: would send email: %s" % message.as_string())
