# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for license information.
# --------------------------------------------------------------------------------------------

from azure.cli.core import AzCommandsLoader
from azure.cli.core.profiles import ResourceType

import azure.cli.command_modules.resource._help  # pylint: disable=unused-import


class ResourceCommandsLoader(AzCommandsLoader):

    def __init__(self, cli_ctx=None):
        super(ResourceCommandsLoader, self).__init__(cli_ctx=cli_ctx)
        self.module_name = __name__
        self.default_resource_type = ResourceType.MGMT_RESOURCE_RESOURCES


    def load_command_table(self, args):
        from azure.cli.command_modules.resource.commands import load_command_table
        super(ResourceCommandsLoader, self).load_command_table(args)
        load_command_table(self, args)
        return self.command_table


    def load_arguments(self, command):
        from azure.cli.command_modules.resource._params import load_arguments
        load_arguments(self, command)
        super(ResourceCommandsLoader, self).load_arguments(command)
