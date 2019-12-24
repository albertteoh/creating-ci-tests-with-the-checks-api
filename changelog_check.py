import datetime
import json
from json import JSONEncoder
import os
import sys
import re

start_release_title_pattern = re.compile(r"^\d+")
release_title_pattern = re.compile(r"^(\d+).(\d+).(\d+) \((.+)\)")
jaeger_client_version_pattern = re.compile(r'JaegerClientVersion = "Go-(\d+).(\d+).(\d+)(.*)"')

class Report:
    def __init__(self, summary, files):
        self.summary = summary
        self.files = files

class File:
    def __init__(self, path, offenses):
        self.path = path
        self.offenses = offenses

class Summary:
    def __init__(self, offense_count):
        self.offense_count = offense_count


class Offense:
    def __init__(self, path="", start_line=0, end_line=0, start_column=0, end_column=0, annotation_level="", message=""):
        self.path = path
        self.start_line = start_line
        self.end_line = end_line
        self.start_column = start_column
        self.end_column = end_column
        self.annotation_level = annotation_level
        self.message = message

class ReportEncoder(json.JSONEncoder):
     def default(self, o):
         return o.__dict__

class Semver:
    def __init__(self, major, minor, patch):
        self.major = major
        self.minor = minor
        self.patch = patch

    def __ne__(self, other):
        return not self == other

    def __eq__(self, other):
        return self.major == other.major and self.minor == other.minor and self.patch == other.patch

    def __gt__(self, other):
        return self.major > other.major or self.minor > other.minor or self.patch > other.patch

    def __str__(self):
        return "{}.{}.{}".format(self.major, self.minor, self.patch)

class Checker:
    def __init__(self):
        self.want = [
            (self.valid_release_title, None),
            (self.valid_next_release_title, None),
        ]
        self.latest_version = None
        self.latest_date = None
        self.changelog_line = 0
        self.constants_line = 0

    def run(self):
        if len(sys.argv) > 1:
            os.chdir(sys.argv[1])

        #print("[DEBUG] currdir={}".format(os.getcwd()))
        #print("[DEBUG] dirs:")
        #dirs = [d for d in os.listdir('.') if os.path.isdir(d)]
        #for d in dirs:
        #    print("[DEBUG] {}".format(d))

        files = []

        self.want.reverse()
        with open("CHANGELOG.md") as changelog:
            changelog_offenses = []
            changelog_file = File("CHANGELOG.md", changelog_offenses)
            files.append(changelog_file)
            for l in changelog:
                if not len(self.want):
                    break

                l = l.strip()
                self.changelog_line += 1

                if not start_release_title_pattern.match(l):
                    continue

                check = self.want.pop()
                #print("checking: '{}'".format(l))
                err = check[0](l)
                if err:
                    changelog_offenses.append(err)
                    break

        with open("constants.go") as constants:
            constants_offenses = []
            constants_file = File("constants.go", constants_offenses)
            files.append(constants_file)
            found_jaeger_client_version = False
            for l in constants:
                l = l.strip()
                self.constants_line += 1

                m = jaeger_client_version_pattern.match(l)
                if m:
                    found_jaeger_client_version = True
                    err = self.valid_jaeger_client_version(m)
                    if err:
                        #print("FAIL", err)
                        constants_offenses.append(err)
                    break

            if not found_jaeger_client_version:
                #print("FAIL", "Could not find JaegerClientVersion in constants.go")
                constants_offenses.append(Offense(
                    path="constants.go",
                    message="Could not find JaegerClientVersion in constants.go",
                ))
        summary = Summary(len(changelog_offenses) + len(constants_offenses))
        report = Report(summary, files)
        print(json.dumps(report, indent=4, cls=ReportEncoder))

    def valid_jaeger_client_version(self, m):
        semver = Semver(m.group(1), m.group(2), m.group(3))
        if self.latest_date == "unreleased" and m.group(4) != "-dev":
            return Offense(
                    path="constants.go",
                    start_line=self.constants_line,
                    end_line=self.constants_line,
                    message="The JaegerClientVersion should  have a '-dev' suffix",
            )

        if semver != self.latest_version:
            return Offense(
                    path="constants.go",
                    start_line=self.constants_line,
                    end_line=self.constants_line,
                    message="JaegerClientVersion ({}) does not match CHANGELOG.md version ({})".format(semver, self.latest_version),
            )

        return None

    def valid_release_title(self, s):
        #print("valid_release_title")
        result = release_title_pattern.search(s)
        if not result:
            return Offense(
                    path="CHANGELOG.md",
                    start_line=self.changelog_line,
                    end_line=self.changelog_line,
                    message="Release title should be in the form <major>.<minor>.<patch> (<date>)"
            )


        self.latest_version = Semver(result.group(1), result.group(2), result.group(3))
        self.latest_date = result.group(4)
        #print("latest version = ", self.latest_version)

        try:
            self.latest_date = datetime.datetime.strptime(self.latest_date,"%Y-%m-%d")
            #print("latest_date={}".format(self.latest_date))
        except:
            if self.latest_date != "unreleased":
                return Offense(
                    path="CHANGELOG.md",
                    start_line=self.changelog_line,
                    end_line=self.changelog_line,
                    message="Date string should be 'unreleased' when in development or in the format YYYY-mm-dd",
            )


        return None

    def valid_next_release_title(self, s):
        #print("valid_next_release_title")
        result = release_title_pattern.search(s)
        if not result:
            return "Release title should be in the form <major>.<minor>.<patch> (<date>)"

        prev_version = Semver(result.group(1), result.group(2), result.group(3))
        #print("prev version = ", self.latest_version)

        if prev_version > self.latest_version:
            return Offense(
                    path="CHANGELOG.md",
                    start_line=self.changelog_line,
                    end_line=self.changelog_line,
                    message="Previous version semver ({}) is greater than latest version semver ({})".format(prev_version, self.latest_version),
            )

        try:
            prev_date = datetime.datetime.strptime(result.group(4),"%Y-%m-%d")
        except:
            return Offense(
                    path="CHANGELOG.md",
                    start_line=self.changelog_line,
                    end_line=self.changelog_line,
                    message="Date string should be in the format YYYY-mm-dd",
            )

        #print("prev_date={}, latest_date={}".format(prev_date, self.latest_date))
        if self.latest_date != "unreleased" and prev_date > self.latest_date:
            return Offense(
                    path="CHANGELOG.md",
                    start_line=self.changelog_line,
                    end_line=self.changelog_line,
                    message="Previous release date ({}) is more recent than latest release date ({})".format(prev_date, self.latest_date),
            )

        return None

def main():
    checker = Checker()
    checker.run()

if __name__ == "__main__":
    main()

#    print('''
#{
#  "metadata": {
#  },
#  "files": [
#    {
#      "path": "Octocat-breeds/octocat.rb",
#      "offenses": [
#        {
#          "severity": "convention",
#          "message": "Style/StringLiterals: Prefer single-quoted strings when you don't need string interpolation or special symbols.",
#          "cop_name": "Style/StringLiterals",
#          "corrected": false,
#          "location": {
#            "start_line": 17,
#            "start_column": 17,
#            "last_line": 17,
#            "last_column": 22,
#            "length": 6,
#            "line": 17,
#            "column": 17
#          }
#        }
#      ]
#    }
#  ],
#  "summary": {
#    "offense_count": 2,
#    "target_file_count": 1,
#    "inspected_file_count": 1
#  }
#}
''')
#    print('''
#{
#  "metadata": {
#    "rubocop_version": "0.60.0",
#    "ruby_engine": "ruby",
#    "ruby_version": "2.3.7",
#    "ruby_patchlevel": "456",
#    "ruby_platform": "universal.x86_64-darwin18"
#  },
#  "files": [
#    {
#      "path": "CHANGELOG.md",
#      "offenses": [
#        {
#          "severity": "convention",
#          "message": "CHANGELOG version should match constants.go",
#          "corrected": false,
#          "location": {
#            "start_line": 1,
#            "start_column": 5,
#            "last_line": 2,
#            "last_column": 9,
#            "length": 2,
#            "line": 1,
#            "column":5 
#          }
#        }
#      ]
#    }
#  ],
#  "summary": {
#    "offense_count": 1,
#    "target_file_count": 1,
#    "inspected_file_count": 1
#  }
#}
#''')
