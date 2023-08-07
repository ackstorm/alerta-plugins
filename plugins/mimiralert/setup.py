from setuptools import setup, find_packages

version = '0.0.1'

setup(
    name="alerta-mimiralert",
    version=version,
    description='Alerta plugin to parser prometheus alerts',
    url='https://github.com/ackstorm/alerta-plugins',
    license='Apache License 2.0',
    author='Juan Carlos Moreno',
    author_email='juancarlos.moreno@',
    packages=find_packages(),
    py_modules=['alerta_mimiralert'],
    install_requires=[
        "requests",
    ],
    include_package_data=True,
    zip_safe=True,
    entry_points={
        'alerta.plugins': [
            'mimiralert = alerta_mimiralert:MimirAlert'
        ]
    }
)
