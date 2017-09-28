# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for license information.
# --------------------------------------------------------------------------------------------
# pylint: disable=unused-import
import azure.cli.command_modules.cdn._help

from azure.cli.core import AzCommandsLoader

class CdnCommandsLoader(AzCommandsLoader):

    def __init__(self, cli_ctx=None):
        super(CdnCommandsLoader, self).__init__(cli_ctx=cli_ctx)
        self.module_name = __name__
        self.min_api = '2017-03-10-profile'


    def load_command_table(self, args):
        from azure.cli.command_modules.cdn.commands import load_command_table
        super(CdnCommandsLoader, self).load_command_table(args)
        load_command_table(self, args)
        return self.command_table


    def load_arguments(self, command):
        from azure.cli.command_modules.cdn._params import load_arguments
        load_arguments(self, command)
        super(CdnCommandsLoader, self).load_arguments(command)
