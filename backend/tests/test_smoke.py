import sys


def test_python_version():
    assert sys.version_info >= (3, 13), "Dự án yêu cầu Python 3.13+"
