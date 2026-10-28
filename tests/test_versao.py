"""A versão do programa segue o versionamento semântico (MAIOR.MENOR.CORREÇÃO)."""

import re

import calibracao


def test_versao_no_formato_semver():
    assert re.fullmatch(r"\d+\.\d+\.\d+", calibracao.__version__)
