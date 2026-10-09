from abc import ABC, abstractmethod
from typing import Protocol


class SignatureVerifier(Protocol):
    def verify(self, payload: bytes, signature: str) -> bool: ...


class Charger(ABC):
    @abstractmethod
    def charge(self, amount: int) -> str:
        raise NotImplementedError

    def refund(self, charge_id: str) -> None:
        raise NotImplementedError
