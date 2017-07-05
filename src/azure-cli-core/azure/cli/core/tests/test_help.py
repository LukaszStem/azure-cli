# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for license information.
# --------------------------------------------------------------------------------------------

from __future__ import print_function

import logging
import sys
import unittest
import mock
from six import StringIO

from azure.cli.core import AzCliCommand
from azure.cli.core.parser import AzCliCommandParser
import azure.cli.core._help as _help
from azure.cli.core._help import ArgumentGroupRegistry

from azure.cli.testsdk import TestCli

from knack.commands import CLICommandsLoader
from knack.help import HelpObject
import knack.help_files

io = {}


def redirect_io(func):
    def wrapper(self):
        global io
        old_stdout = sys.stdout
        old_stderr = sys.stderr
        sys.stdout = sys.stderr = io = StringIO()
        func(self)
        io.close()
        sys.stdout = old_stdout
        sys.stderr = old_stderr

    return wrapper


class HelpTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Ensure initialization has occurred correctly
        logging.basicConfig(level=logging.DEBUG)

    @classmethod
    def tearDownClass(cls):
        logging.shutdown()

    @redirect_io
    def test_help_long_description_from_docstring(self):
        """ Verifies that the first sentence of a docstring is extracted as the short description.
        Verifies that line breaks in the long summary are removed and leaves the text wrapping
        to the help system. """

        def test_handler():
            """Short Description. Long description with\nline break."""
            pass

        setattr(sys.modules[__name__], test_handler.__name__, test_handler)

        cli_command(None, 'test', '{}#{}'.format(__name__, test_handler.__name__))
        _update_command_definitions(command_table)

        config = Configuration()
        app = Application(config)

        with self.assertRaises(SystemExit):
            app.execute('test -h'.split())
        self.assertEqual(True, io.getvalue().startswith(
            '\nCommand\n    az test: Short Description.\n        Long description with line break.'))  # pylint: disable=line-too-long

    def test_help_loads(self):
        cli = TestCli()
        from azure.cli.core.commands.arm import add_id_parameters
        parser_dict = {}
        cli = TestCli()
        cli.invoke(['-h'])
        cmd_tbl = app.configuration.get_command_table()
        app.parser.load_command_table(cmd_tbl)
        for cmd in cmd_tbl:
            try:
                app.configuration.load_params(cmd)
            except KeyError:
                pass
        app.register(app.COMMAND_TABLE_PARAMS_LOADED, add_id_parameters)
        app.raise_event(app.COMMAND_TABLE_PARAMS_LOADED, command_table=cmd_tbl)
        app.parser.load_command_table(cmd_tbl)
        _store_parsers(app.parser, parser_dict)

        for name, parser in parser_dict.items():
            try:
                help_file = _help.GroupHelpFile(name, parser) \
                    if _is_group(parser) \
                    else _help.CommandHelpFile(name, parser)
                help_file.load(parser)
            except Exception as ex:
                raise _help.HelpAuthoringException('{}, {}'.format(name, ex))


def _store_parsers(parser, d):
    for s in parser.subparsers.values():
        d[_get_parser_name(s)] = s
        if _is_group(s):
            for c in s.choices.values():
                d[_get_parser_name(c)] = c
                _store_parsers(c, d)


def _is_group(parser):
    return getattr(parser, 'choices', None) is not None


def _get_parser_name(parser):
    # pylint:disable=protected-access
    return (parser._prog_prefix if hasattr(parser, '_prog_prefix') else parser.prog)[len('az '):]


if __name__ == '__main__':
    unittest.main()
