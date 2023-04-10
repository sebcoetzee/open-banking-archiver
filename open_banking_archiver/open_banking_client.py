import logging
from datetime import datetime, timedelta

from nordigen import NordigenClient  # type: ignore
from nordigen.types.types import TokenType  # type: ignore
from open_banking_archiver.config import resolve_config

logger = logging.getLogger(__name__)


class OpenBankingClient(NordigenClient):
    def __init__(
        self, secret_key: str, secret_id: str, timeout: int = 10, base_url: str = "https://ob.nordigen.com/api/v2"
    ) -> None:
        super().__init__(secret_key, secret_id, timeout, base_url)
        self.token_generated = datetime(1970, 1, 1)
        self.token_expires: int = 0
        self.token_refresh: str = ""
        self.token_refresh_expires: int = 0

    def generate_token(self) -> TokenType:
        token = super().generate_token()
        self.token_expires = token["access_expires"]
        self.token_refresh = token["refresh"]
        self.token_refresh_expires = token["refresh_expires"]
        self.token_generated = datetime.now()
        return token

    def exchange_token(self, refresh_token: str) -> TokenType:
        token = super().exchange_token(refresh_token)
        self.token_expires = token["access_expires"]
        self.token_generated = datetime.now()
        return token

    def refresh_token(self) -> None:
        elapsed_time = datetime.now() - self.token_generated
        if elapsed_time > timedelta(seconds=self.token_expires - 60):
            if elapsed_time > timedelta(seconds=self.token_refresh_expires - 60):
                self.generate_token()
                logger.debug("Refresh token expired. Generated completely new token.")
            else:
                self.exchange_token(self.token_refresh)
                logger.debug("Exchanged token using the refresh token.")
        else:
            logger.debug("Exchange token still valid.")


OPEN_BANKING_CLIENT = OpenBankingClient(resolve_config().nordigen_secret_key, resolve_config().nordigen_secret_id)
