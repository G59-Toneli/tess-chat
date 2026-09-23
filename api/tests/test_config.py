"""Validação do .env no boot."""

import pytest
from pydantic import ValidationError

from app.config import JWT_SECRET_DEV, Settings


@pytest.mark.parametrize("segredo", [JWT_SECRET_DEV, "curto-demais"])
def test_prod_recusa_segredo_de_dev_ou_curto(segredo):
    with pytest.raises(ValidationError, match="JWT_SECRET"):
        Settings(_env_file=None, database_url="x", env="prod", jwt_secret=segredo)


def test_prod_aceita_segredo_proprio_longo():
    s = Settings(_env_file=None, database_url="x", env="prod", jwt_secret="a" * 32)
    assert s.jwt_secret == "a" * 32


def test_dev_aceita_o_segredo_de_dev():
    assert Settings(_env_file=None, database_url="x", env="dev").jwt_secret == JWT_SECRET_DEV
