"""Account-Service für ezbookkeeping Accounts."""

import logging

from baezi.api.client import EzbookkeepingClient
from baezi.models import Account

logger = logging.getLogger(__name__)


class AccountService:
    """Service für Account-Management."""

    def __init__(self, api_client: EzbookkeepingClient):
        """Initialisiert Account-Service.

        Args:
            api_client: ezbookkeeping API-Client
        """
        self.api = api_client
        self._account_map: dict[str, str] = {}

    def load_account_map(self) -> dict[str, str]:
        """Lädt Account-Mapping von Banking4-ID zu ezbookkeeping-ID.

        Returns:
            Dictionary: B4AccID -> ezbookkeeping Account ID

        Raises:
            APIError: Bei API-Fehlern
        """
        logger.info("Lade Account-Mapping...")

        resp = self.api.get_accounts()

        if not resp.get("success"):
            logger.warning("⚠️  Konnte Accounts nicht laden")
            return {}

        account_map = {}

        for acc_data in resp["result"]:
            account = Account.from_api_response(acc_data)

            if account.b4_account_id:
                account_map[account.b4_account_id] = account.id
                logger.debug(
                    f"  ✓ Account gemappt: B4AccID {account.b4_account_id} "
                    f"→ ezb '{account.name}' (ID: {account.id})"
                )

        self._account_map = account_map
        logger.info(f"✓ {len(account_map)} Konten gemappt (über B4AccID im Kommentarfeld)")

        return account_map

    def get_ezb_account_id(self, b4_account_id: str) -> str | None:
        """Gibt ezbookkeeping Account-ID für Banking4 Account zurück.

        Args:
            b4_account_id: Banking4 Account-ID

        Returns:
            ezbookkeeping Account-ID oder None
        """
        return self._account_map.get(b4_account_id)

    def has_account(self, b4_account_id: str) -> bool:
        """Prüft ob Account existiert.

        Args:
            b4_account_id: Banking4 Account-ID

        Returns:
            True wenn Account existiert
        """
        return b4_account_id in self._account_map
