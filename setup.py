from setuptools import find_packages
from distutils.core import setup

DESC = 'Library for creating circuits that encode discrete'
'distributions. The name comes from the random bit model of drawing'
'from discrete distributions using coin flips.'

setup(
    name='py-aiger-coins',
    version='0.0.0',
    description=DESC,
    url='http://github.com/mvcisback/py-aiger-coins',
    author='Marcell Vazquez-Chanlatte',
    author_email='marcell.vc@eecs.berkeley.edu',
    license='MIT',
    install_requires=[
        'py-aiger',
        'py-aiger-bv',
        'dd',
        'bidict',
        'parsimonious',
    ],
    packages=find_packages(),
)
