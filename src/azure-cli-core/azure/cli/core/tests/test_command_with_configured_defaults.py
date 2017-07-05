# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for license information.
# --------------------------------------------------------------------------------------------
import os
import logging
import unittest
import mock

from azure.cli.core import AzCliCommand, AzCommandsLoader

from azure.cli.testsdk import TestCli

from knack.config import CLIConfig


# a dummy callback for arg-parse
def load_params(_):
    pass


class TestCommandWithConfiguredDefaults(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        # Ensure initialization has occurred correctly
        logging.basicConfig(level=logging.DEBUG)

    @classmethod
    def tearDownClass(cls):
        logging.shutdown()

    def set_up_command_table(self, required_arg=False):

        class TestCommandsLoader(AzCommandsLoader):

            def sample_vm_list(resource_group_name):
                return resource_group_name

            def load_command_table(self, args):
                super(TestCommandsLoader, self).load_command_table(args)
                command = AzCliCommand(self.ctx, 'test sample-vm-list', sample_vm_list)
                command.add_argument('resource_group_name', ('--resource-group-name', '-g'),
                                     configured_default='group', required=required_arg)
                self.command_table['test sample-vm-list'] = command
                return self.command_table

        return TestCli(commands_loader_cls=TestCommandsLoader)


    def test_apply_configured_defaults_on_required_arg(self):
        cli = self.set_up_command_table(required_arg=True)
        mock.patch.dict({cli.config.env_var_name('defaults', 'group'): 'myRG'})
        argv = 'az test sample-vm-list'.split()

        # action
        res = cli.invoke(argv[1:])

        # assert
        self.assertEqual(res.result, 'myRG')

    def test_apply_configured_defaults_on_optional_arg(self):
        cli = self.set_up_command_table(required_arg=False)
        mock.patch.dict({cli.config.env_var_name('defaults', 'group'): 'myRG'})
        argv = 'az test sample-vm-list'.split()

        # action
        res = cli.invoke(argv[1:])

        # assert
        self.assertEqual(res.result, 'myRG')


if __name__ == '__main__':
    unittest.main()
