"""Configuration to connect to a PostgreSQL database."""

# Standard Python Libraries
from configparser import ConfigParser
import platform

# Third-Party Libraries
from importlib_resources import files

myplatform = platform.system()


REPORT_DB_CONFIG = files("pe_reports").joinpath("data/database.ini")

# print(REPORT_DB_CONFIG)

if myplatform != "Darwin":

    def config(filename=REPORT_DB_CONFIG, section="postgres"):
        """Parse Postgres configuration details from database configuration file."""
        parser = ConfigParser()

        parser.read(filename, encoding="utf-8")

        db = dict()

        if parser.has_section(section):
            for key, value in parser.items(section):
                if value != "":
                    db[key] = value
                else:
                    raise Exception(
                        f"The value for parameter being"
                        f" parsed is empty. Please place credentials in {REPORT_DB_CONFIG}"
                    )

        else:
            raise Exception(f"Section {section} not found in {filename}")

        return db

else:

    def config(filename=REPORT_DB_CONFIG, section="postgreslocal"):
        """Parse Postgres configuration details from database configuration file."""
        parser = ConfigParser()

        parser.read(filename, encoding="utf-8")

        db = dict()

        if parser.has_section(section):
            for key, value in parser.items(section):
                db[key] = value

        else:
            raise Exception(f"Section {section} not found in {filename}")

        return db
