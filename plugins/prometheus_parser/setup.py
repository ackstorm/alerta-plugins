from setuptools import setup, find_packages

version = '0.0.1'

setup(
    name="alerta-prometheus-parser",
    version=version,
    description='Alerta plugin for ackstorm',
    url='https://github.com/ackstorm/alerta-plugins',
    license='Apache License 2.0',
    author='Juan Carlos Moreno',
    author_email='juancarlos.moreno@',
    packages=find_packages(),
    py_modules=['prometheus_parser'],
    install_requires=[
        "requests",
    ],
    include_package_data=True,
    zip_safe=True,
    entry_points={
        'alerta.plugins': [
            'promparser = prometheus_parser:PrometheusParser'
        ]
    }
)
