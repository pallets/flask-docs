from setuptools import setup


setup(
    name='Flask-Docbuilder',
    license='BSD',
    author='Armin Ronacher',
    author_email='armin.ronacher@active-4.com',
    py_modules=['docbuilder'],
    install_requires=[
        'click>=2.0',
    ],
    classifiers=[
        'PRIVATE DO NOT UPLOAD',
    ],
    entry_points='''
        [console_scripts]
        flask-docbuilder=docbuilder:cli
    ''',
)
