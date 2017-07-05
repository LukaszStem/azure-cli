# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for license information.
# --------------------------------------------------------------------------------------------

from azure.cli.core import AzCommandsLoader

class RedisCommandsLoader(AzCommandsLoader):

    def __init__(self, ctx=None):
        super(RedisCommandsLoader, self).__init__(ctx=ctx)
        self.module_name = __name__
        self.min_api='2017-03-10-profile'


    def load_command_table(self, args):
        from azure.cli.command_modules.redis.commands import load_command_table
        super(RedisCommandsLoader, self).load_command_table(args)
        load_command_table(self, args)
        return self.command_table


    def load_arguments(self, command):
        from azure.cli.command_modules.redis._params import load_arguments
        load_arguments(self, command)
        super(RedisCommandsLoader, self).load_arguments(command)
