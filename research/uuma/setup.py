# Author & builder: Juan-louw Greyling <juanlouw.greyling@gmail.com>
from setuptools import setup, Extension
setup(ext_modules=[Extension("uuma_native", ["native/uuma_native/uuma_native.c"], extra_compile_args=["-O2"])])
