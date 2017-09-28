# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for license information.
# --------------------------------------------------------------------------------------------

from __future__ import print_function
import sys

from azure.cli.core.commands import ExtensionCommandSource
import azure.cli.core.azlogging as azlogging

from knack.help_files import _load_help_file
from knack.help import \
    (HelpExample, CommandHelpFile, GroupHelpFile, HelpFile as KnackHelpFile, CLIHelp,
     ArgumentGroupRegistry as KnackArgumentGroupRegistry, print_description_list, _print_indent,
     print_detailed_help)
from knack.log import get_logger

logger = get_logger(__name__)

PRIVACY_STATEMENT = """
Welcome to Azure CLI!
---------------------
Use `az -h` to see available commands or go to https://aka.ms/cli.

Telemetry
---------
The Azure CLI collects usage data in order to improve your experience.
The data is anonymous and does not include commandline argument values.
The data is collected by Microsoft.

You can change your telemetry settings with `az configure`.
"""

WELCOME_MESSAGE = """
    /\\
   /  \\    _____   _ _ __ ___
  / /\ \\  |_  / | | | \'__/ _ \\
 / ____ \\  / /| |_| | | |  __/
/_/    \_\\/___|\__,_|_|  \___|


Welcome to the cool new Azure CLI!

Here are the base commands:
"""

class AzCliHelp(CLIHelp):

    def __init__(self, cli_ctx):
        self.cli_ctx = cli_ctx
        super(AzCliHelp, self).__init__(cli_ctx, PRIVACY_STATEMENT, WELCOME_MESSAGE)


# TODO: This is different for CLI Extensions!
def print_detailed_help(cli_name, help_file):
    _print_extensions_msg(help_file)
    _print_header(cli_name, help_file)

    if help_file.type == 'command':
        _print_indent('Arguments')
        print_arguments(help_file)
    elif help_file.type == 'group':
        _print_groups(help_file)

    if help_file.examples:
        _print_examples(help_file)

# TOOD: Needed for CLI Extensions!
def _print_extensions_msg(help_file):
    if help_file.type != 'command':
        return
    if help_file.command_source and isinstance(help_file.command_source, ExtensionCommandSource):
        logger.warning(help_file.command_source.get_command_warn_msg())



class CliHelpFile(KnackHelpFile):

    def __init__(self, delimiters):
        super(CliHelpFile, self).__init__(delimiters)

    # TODO: Needed enhancement!!!
    @staticmethod
    def _should_include_example(ex):
        min_profile = ex.get('min_profile')
        max_profile = ex.get('max_profile')
        if min_profile or max_profile:
            from azure.cli.core.profiles import supported_api_version, PROFILE_TYPE
            # yaml will load this as a datetime if it's a date, we need a string.
            min_profile = str(min_profile) if min_profile else None
            max_profile = str(max_profile) if max_profile else None
            return supported_api_version(PROFILE_TYPE,
                                            min_api=min_profile,
                                            max_api=max_profile)
        return True

    # Needs to override base implementation
    def _load_from_data(self, data):
        if not data:
            return

        if isinstance(data, str):
            self.long_summary = data
            return

        if 'type' in data:
            self.type = data['type']

        if 'short-summary' in data:
            self.short_summary = data['short-summary']

        self.long_summary = data.get('long-summary')

        if 'examples' in data:
            self.examples = []
            for d in data['examples']:
                if CliHelpFile._should_include_example(d):
                    self.examples.append(HelpExample(d))


class ArgumentGroupRegistry(KnackArgumentGroupRegistry):  # pylint: disable=too-few-public-methods

    def __init__(self, group_list):

        super(ArgumentGroupRegistry, self).__init__(group_list)
        self.priorities = {
            None: 0,
            'Resource Id Arguments': 1,
            'Generic Update Arguments': 998,
            'Global Arguments': 1000,
        }
        priority = 2
        # any groups not already in the static dictionary should be prioritized alphabetically
        other_groups = [g for g in sorted(list(set(group_list))) if g not in self.priorities]
        for group in other_groups:
            self.priorities[group] = priority
            priority += 1
