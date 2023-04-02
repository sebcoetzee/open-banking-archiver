import logging
import smtplib
from email.message import EmailMessage

from jinja2 import Environment
from jinja2.loaders import PackageLoader
from open_banking_archiver.config import resolve_config
from open_banking_archiver.model import Bank

JINJA_ENV = Environment(loader=PackageLoader("open_banking_archiver"))

logger = logging.getLogger(__name__)


class Email:
    def __init__(self) -> None:
        self.smtp = smtplib.SMTP_SSL(resolve_config().smtp_host, resolve_config().smtp_port, timeout=10000)
        self.smtp.login(resolve_config().smtp_username, resolve_config().smtp_password)
        self.from_email = resolve_config().from_email

    def send_link(self, to_email: str, bank: Bank, link: str) -> None:
        template = JINJA_ENV.get_template("bank_account_link_email.j2")
        msg = EmailMessage()
        msg["Subject"] = "Open Banking Connection Activation"
        msg["From"] = self.from_email
        msg["To"] = to_email
        msg.set_content(template.render(bank=bank, link=link))
        logger.debug("Sending email : %s", msg.as_string())
        self.smtp.sendmail(self.from_email, to_email, msg.as_string())
