# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for license information.
# --------------------------------------------------------------------------------------------

from azure.cli.core import AzCommandsLoader

import azure.cli.command_modules.network._help  # pylint: disable=unused-import


class NetworkCommandsLoader(AzCommandsLoader):

    def load_command_table(self, args):
        from azure.cli.command_modules.network.commands import load_command_table
        super(NetworkCommandsLoader, self).load_command_table(args)
        load_command_table(self, args)
        return self.command_table


    def load_arguments(self, command):
        from azure.cli.command_modules.network._params import load_arguments
        load_arguments(self, command)
        super(NetworkCommandsLoader, self).load_arguments(command)
