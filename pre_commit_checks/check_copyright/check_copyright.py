# Copyright (c) 2019 Intel Corporation
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

""" This module checks copyright of the repository C/C++ files """

# Example of usage:
#     python check_copyright.py
#      --repo_path .\mdp_msdk-lib \
#      --commit_id d593b26b104128541799758a1278ed497cabc91b \
#      --report_path .\pre_commit_checks.json

import argparse
import re
import sys

import pathlib
import git

sys.path.append(str(pathlib.Path(__file__).resolve().parents[2]))
from common import helper

YEAR = 2019  # Year of copyright
FILES_TO_CHECK = ('.h', '.cpp', '.c') # only file extensions can be added
SUBSTRING_IS_NOT_FOUND = -1

def get_leading_comments(stream):
    """
    Returns the leading comments in C/C++ context from begin to the first not comment symbol

    : param stream: string stream
    """
    comments = []
    multiline_comment = False

    for line in stream:
        line = line.strip()

        if not line:
            continue

        if not multiline_comment:
            found_pos = line.find('/*')
            if found_pos >= 0:
                if line.find('*/', found_pos) == SUBSTRING_IS_NOT_FOUND:
                    multiline_comment = True
                comments.append(line)
                continue

            if line.find('//') >= 0:
                comments.append(line)
                continue

            break

        if multiline_comment:
            if line.find('*/') >= 0:
                multiline_comment = False
            comments.append(line)
            continue
    return comments


def get_copyright_strings(tested_strings):
    """
    Checks input strings and returns them in list

    :param tested_strings: The list of some stings
    :return: The list of selected strings
    """
    copyright_strings = []

    for tested_string in tested_strings:
        if re.search(r'.*[Cc]opyright\s?.*([0-9]{4}).*', tested_string):
            copyright_strings.append(tested_string)

    return copyright_strings


def is_intel_copyright(tested_string):
    """
    Checks is copyright string the Intel copyright

    :param tested_strings: The tested string
    :return: The test result in Dict or False
    """
    return re.search(r'.*Copyright\s*?\([cC]\)\s*[0-9 \-]*'
                     r'\s*?Intel\s*?Corporation.*', tested_string)

def get_copyright_year_or_range(tested_string):
    """
    Returns copyright dates

    :param tested_string: The tested string
    :return: The year or range result in Dict or False
    """
    # Check copyright range correctness
    substring = re.search(r'([0-9]{4}\ ?\-\ ?)?([0-9]{4})', tested_string)
    if not substring:
        return None

    years = substring.group(0).split('-')
    years = [int(year) for year in years]

    if len(years) == 2:
        return {'range': years}

    return {'year': years[0]}


class CopyrightChecker:
    """ This class checks copyright of the repository C/C++ files"""

    def __init__(self, repo_path, commit_id, report_path):
        self.repo_path = pathlib.Path(repo_path)
        self.commit_id = commit_id
        self.report_path = pathlib.Path(report_path)
        self.details = []
        self.src_file = ""

    def get_changed_files(self):
        """
        Get list of changed files in received commit relatively to previous commit.
        Uses git repository and git commands.

        :param: None
        return file_paths: Path

        """
        repo = git.Repo(self.repo_path)
        # Get full diff without deleted(d) files
        files = repo.git.diff(self.commit_id + "~1", name_only=True, diff_filter='d')
        files = files.splitlines() # List of changed files

        file_paths = []
        for src_file in files:
            if src_file.endswith(FILES_TO_CHECK):
                file_paths.append(pathlib.Path(src_file)) # Changed file paths after filtering by
                                                          # file extension
        return file_paths

    def append_details(self, string):
        """
        Update details sting list
        """
        self.details.append(str(self.src_file) + ':')
        self.details.append(string)

    def is_copyright_correct(self, tested_strings):
        """
        Checks the copyright strings list, returns True if copyright correct

        :param src_file: The path to source file from repository root
        :param tested_strings: The string list with copyright data
        :param details: The string list where to put descriptions

        :return: True if no copyright problems present
        """
        copyright_strings = get_copyright_strings(tested_strings)

        if not copyright_strings:
            self.append_details("\tMissing copyright.")
            return False

        intel_copyright = ""
        # Check that no intel copyright presents or intel copyrihts present once
        for copyright_string in copyright_strings:
            if is_intel_copyright(copyright_string):
                if intel_copyright:
                    self.append_details(f"\tToo many copyrights: \n\t{copyright_strings}")
                    return False
                intel_copyright = copyright_string

        if not intel_copyright:
            # Copyrights are correct, third party copyrights
            return True

        year_or_range = get_copyright_year_or_range(intel_copyright)

        if not year_or_range:
            self.append_details(f"\tIncorrect the copyright range need {YEAR} "
                                f"or [YEAR-]{YEAR} ex: 2014-{YEAR}\n\t{intel_copyright}")
            return False

        if 'year' in year_or_range and not year_or_range['year'] == YEAR:
            self.append_details(f"\tIncorrect the copyright year, [YEAR-]{YEAR} is needed"
                                f":\n\t{intel_copyright}")
            return False

        if 'range' in year_or_range:
            from_year, to_year = year_or_range['range']

            if not to_year == YEAR or to_year <= from_year:
                self.append_details(f"\tIncorrect the copyright range "
                                    f"[YEAR-]{YEAR} is needed\n\t{intel_copyright}")
                return False

        # Copyrights are correct, Intel copyright
        return True


    def check_copyright(self):
        """
        Checks copyrights in all files which returned by function get_changed_files.
        Copyrights are checked by regexs line by line.
        Before the exit calls function update_json to store results.

        :param: None
        :return: None
        """
        summary = ["-" * 50]
        files = self.get_changed_files()
        has_problems = False

        for self.src_file in files:
            comments = []

            with open(self.repo_path / self.src_file) as file_desr:
                comments = get_leading_comments(file_desr)

            has_problems |= not self.is_copyright_correct(comments)

        if has_problems:
            summary.append("Copyright check FAILED!")
            summary.append("")

            self.details.append(f"\nCorrect format: Copyright (c) [YEAR-]{YEAR} Intel "
                                f"Corporation. All Rights Reserved.")
            output = "\n".join(summary + self.details)

            print(output)

            if not helper.update_json("check_copyright", False, output, self.report_path):
                print(f"Cannot update json file: {self.report_path}")
                print("No report will be posted!")
                exit(2) # Fail because of infrastructure
            exit(1)

        else:
            summary.append("Copyright check PASSED!")
            summary.append("")
            self.details.append("Checked following files:")

            if not files:
                self.details.append("\tNo files to check...")
                self.details.append(f"\tCheck works only for files with extensions:"
                                    f"{FILES_TO_CHECK}")

            for file_name in files:
                self.details.append("\t" + str(file_name))
            output = "\n".join(summary + self.details)

            print(output)

            if not helper.update_json("check_copyright", True, output, self.report_path):
                print(f"Cannot update json file: {self.report_path}")
                print("No report will be posted!")
                exit(2) # Fail because of infrastructure
            exit(0)


def main():
    """ Parses program arguments, creates CopyrightChecker instance and runs copyright check """
    parser = argparse.ArgumentParser()
    parser.add_argument("-r", "--repo-path", metavar="String",
                        help="Path to the folder where repo is located (full or absolute).")
    parser.add_argument("-c", "--commit-id", metavar="String",
                        help="Commit regarding which need to watch the changes.")
    parser.add_argument("-p", "--report-path", metavar="String",
                        help="Path to the json where should be stored pre-commit check results \
(prefered name is 'pre_commit_checks.json').")
    args = parser.parse_args()

    copyright_checker = CopyrightChecker(args.repo_path, args.commit_id, args.report_path)
    copyright_checker.check_copyright()

if __name__ == '__main__':
    main()
