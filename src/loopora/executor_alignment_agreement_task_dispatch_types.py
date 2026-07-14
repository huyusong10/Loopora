from __future__ import annotations

from collections.abc import Callable

LocalizedAgreementFactories = tuple[Callable[[str], dict], Callable[[str], dict], Callable[[str], dict]]
AgreementTaskFactoryRoute = tuple[Callable[[str], bool], LocalizedAgreementFactories]
