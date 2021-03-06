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

import git
import sys
import pathlib
import argparse
import logging

sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))
from common import logger_conf
from common.helper import ErrorCode


class Checker:
    def __init__(self, repo_path, revision):
        self.repo = git.Repo(pathlib.Path(repo_path))
        self.revision = revision
        self.log = logging.getLogger(self.__class__.__name__)

    def _get_author_info(self):
        self.log.info(f'Getting author information for {self.revision} revision.')
        commit = self.repo.commit(self.revision)
        self.log.info(f'Author name: {commit.author.name}')
        self.log.info(f'Author email: {commit.author.email}')
        return commit.author.name, commit.author.email

    def check_author(self, author):
        incorrect_author_names = ['root', 'mediasdk']

        if author not in incorrect_author_names:
            self.log.info('Author name is correct')
            return True
        self.log.error(f'Author name can not be {", ".join(incorrect_author_names)}.')
        return False

    def check_email(self, email):
        incorrect_email_endswith = '@localhost.localdomain'

        if not email.endswith(incorrect_email_endswith):
            self.log.info('Author email is correct')
            return True
        self.log.error(f'Author email can not ends in {incorrect_email_endswith}.')
        return False

    def check(self):
        author, email = self._get_author_info()

        check_author_result = self.check_author(author)
        check_email_result = self.check_email(email)

        if check_author_result and check_email_result:
            self.log.info("All checks PASSED")
        else:
            self.log.error("Some checks FAILED")

        return check_author_result and check_email_result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-p", "--repo-path", metavar="String",
                        help="Path to repository")
    parser.add_argument("-r", "--revision", metavar="String",
                        help="Revision to check")
    args = parser.parse_args()
    logger_conf.configure_logger()

    checker = Checker(repo_path=args.repo_path, revision=args.revision)
    if checker.check():
        exit(0)
    exit(ErrorCode.CRITICAL.value)

if __name__ == '__main__':
    main()
