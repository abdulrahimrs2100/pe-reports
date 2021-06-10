"""A tool for creating Posture & Exposure reports.

Usage:
    pe-reports REPORT_DATE DATA_DIRECTORY OUTPUT_DIRECTORY

Arguments:
  REPORT_DATE       Date of the report, format YYYY-MM-DD.
  DATA_DIRECTORY    The directory where the excel data files are located.
                    Organized by owner.
  OUTPUT_DIRECTORY  The directory where the final PDF reports should be saved.

Options:
  -h --help     Show this message.
  -v --version  Show version information.
"""

# Standard Python Libraries
import os
import sys
from typing import Dict

# Third-Party Libraries
import docopt
import pkg_resources
from pptx import Presentation

from ._version import __version__
from .pages import Pages

# Configuration
REPORT_SHELL = pkg_resources.resource_filename("pe_reports", "data/shell/pe_shell.pptx")


def load_template():
    """Load PowerPoint template into memory."""
    prs = Presentation(REPORT_SHELL)
    return prs


def export_set(prs):
    """Export PowerPoint report set to output directory."""
    try:
        pptx_out = "Customer_ID_Posture_Exposure.pptx"
        prs.save(os.path.join("/output", pptx_out))
    except OSError:
        print("No output available.")
    return


def generate_reports(data, data_dir, out_dir):
    """Gather assets to produce reports."""
    # TODO: build code to connect customer db, encrypt and embed pdf reports. Issue #7: https://github.com/cisagov/pe-reports/issues/7


def main():
    """Set up logging and call the pe_reprots function."""
    args: Dict[str, str] = docopt.docopt(__doc__, version=__version__)

    # TODO: Add generate_reports func to handle cmd line arguments and function. Issue #8: https://github.com/cisagov/pe-reports/issues/8
    generate_reports(
        args["REPORT_DATE"], args["DATA_DIRECTORY"], args["OUTPUT_DIRECTORY"]
    )

    """Generate PDF reports."""
    print("\n [Info] Loading Posture & Exposure Report Template, Version:", __version__)
    prs = load_template()

    print("\n [Info] Generating Graphs ")
    Pages.cover(prs)
    Pages.overview(prs)
    export_set(prs)


if __name__ == "__main__":
    sys.exit(main())
