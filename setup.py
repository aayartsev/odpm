import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="odpm",
    version="0.0.8",
    author="Yartsev Alexander",
    author_email="a.yartsev@yartsev.by",
    description="odoo development project mananagement",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/aayartsev/odpm",
    packages=setuptools.find_packages(),
    license="LGPLv3",
    python_requires=">=3",
    install_requires=[],
    include_package_data=True,
    entry_points={
        'console_scripts': ['odpm = odpm.odpm:main'],
    },
    classifiers=[
          "Development Status :: 4 - Beta",
          "Intended Audience :: Developers",
          "License :: OSI Approved :: GNU Lesser General Public License v3 (LGPLv3)",
          "License :: OSI Approved :: GNU Lesser General Public License v3 or later (LGPLv3+)",
          "Programming Language :: Python",
          "Programming Language :: Python :: 3",
          "Topic :: Internet",
          "Topic :: Software Development :: Libraries",
          "Topic :: Software Development :: Libraries :: Python Modules"],
      keywords="odoo odpm"
)