# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for license information.
# --------------------------------------------------------------------------------------------

from azure.cli.core.profiles import ResourceType
from azure.cli.core.profiles._shared import get_versioned_sdk_path

from knack.arguments import ignore_type, ArgumentsContext
from knack.commands import CommandSuperGroup, CommandGroup as KnackCommandGroup, CLICommandsLoader
from knack.util import CLIError

# COMMANDS UTILITIES

CLI_COMMAND_KWARGS = ['transform', 'table_transformer', 'confirmation', 'exception_handler', 'min_api', 'max_api',
                      'client_factory', 'operations_tmpl', 'no_wait_param', 'validator']


class CliCommandType(object):

    def __init__(self, overrides=None, **kwargs):
        if isinstance(overrides, str):
            raise ValueError("Overrides has to be a {} (cannot be a string)".format(CliCommandType.__name__))
        unrecognized_kwargs = [x for x in kwargs if x not in CLI_COMMAND_KWARGS]
        if unrecognized_kwargs:
            raise TypeError('unrecognized kwargs: {}'.format(unrecognized_kwargs))
        self.settings = {}
        self.update(overrides, **kwargs)

    def update(self, other=None, **kwargs):
        if other:
            self.settings.update(**other.settings)
        self.settings.update(**kwargs)

class _CommandGroup(KnackCommandGroup):

    def __init__(self, module_name, command_loader, group_name, command_type=None, **kwargs):
        if command_type:
            if not isinstance(command_type, CliCommandType):
                raise TypeError("command_type expected type '{}', got '{}'".format(
                    CliCommandType.__name__, type(command_type)))
            command_type.update(**kwargs)
        else:
            command_type = CliCommandType(kwargs)
        self.group_command_type = command_type
        super(_CommandGroup, self).__init__(module_name, command_loader, group_name,
                                           command_type.settings.get('operations_tmpl'))

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    def command(self, name, method_name, command_type=None, **kwargs):
        """
        Register a CLI command
        :param name: Name of the command as it will be called on the command line
        :type name: str
        :param method_name: Name of the method the command maps to
        :type method_name: str
        :param command_type: CliCommandType object containing settings to apply to the entire command group
        :type command_type: CliCommandType
        :param kwargs: Keyword arguments. Supported keyword arguments include:
            - confirmation: Prompt prior to the action being executed. This is useful if the action
                            would cause a loss of data. (bool)
            - transform: Transform function for transforming the output of the command (function)
            - table_transformer: Transform function or JMESPath query to be applied to table output to create a
                                 better output format for tables. (function or string)
            - exception_handler: Exception handler for handling non-standard exceptions (function)
            - resource_type: The ResourceType enum value to use with min or max API.
            - min_api: Minimum API version required for commands within the group (string)
            - max_api: Maximum API version required for commands within the group (string)
        :rtype: None
        """
        merged_command_type = None
        if command_type:
            if not isinstance(command_type, CliCommandType):
                raise TypeError("command_type expected type '{}', got '{}'".format(
                    CliCommandType.__name__, type(command_type)))
            command_type.update(**kwargs)
            merged_command_type = CliCommandType(overrides=self.group_command_type, **command_type.settings)
        else:
            merged_command_type = self.group_command_type

        operations_tmpl = merged_command_type.settings.get('operations_tmpl')
        command_name = '{} {}'.format(self.group_name, name) if self.group_name else name
        merged_kwargs = merged_command_type.settings.copy()
        merged_kwargs.update(kwargs)
        self.command_loader._cli_command(command_name,
                                         operations_tmpl.format(method_name), **merged_kwargs)


    def generic_update_command(self, name,
                               getter_name='get', getter_type=None,
                               setter_name='create_or_update', setter_type=None, setter_arg_name='parameters', 
                               custom_func_name=None, custom_func_type=None,
                               child_collection_prop_name=None, child_collection_key='name', child_arg_name='item_name',
                               **kwargs):
        if bool(custom_func_name) != bool(custom_func_type):
            raise CLIError('Command authoring error: to enable custom arguments, both `custom_func_name` and '
                            '`custom_func_type` must be provided.')
        elif custom_func_name:
            # TODO: Make this work
            custom_function_op = None

        self.command_loader.cli_generic_update_command(
            self.module_name,
            '{} {}'.format(self.group_name, name),
            self.operations_tmpl.format(getter_name),
            self.operations_tmpl.format(setter_name),
            factory=self._client_factory,
            custom_function_op=custom_function_op,
            setter_arg_name=setter_arg_name)

    def generic_wait_command(self, name, getter_name, command_type=None, **kwargs):
        pass


# PARAMETERS UTILITIES

def patch_arg_make_required(argument):
    argument.type.settings['required'] = True


def patch_arg_make_optional(argument):
    argument.type.settings['required'] = False


def patch_arg_update_description(description):
    def _patch_action(argument):
        argument.type.settings['help'] = description

    return _patch_action


class _ParametersContext(ArgumentsContext):

    def __init__(self, command_loader, scope, **kwargs):
        super(_ParametersContext, self).__init__(command_loader, scope)
        self.scope = scope  # this is called "command" in knack, but that is not an accurate name
        self.group_kwargs = kwargs

    def argument(self, argument_name, arg_type=None, **kwargs):
        kwargs.update(self.group_kwargs)
        super(_ParametersContext, self).argument(argument_name, arg_type=arg_type, **kwargs)

    def alias(self, argument_name, options_list, **kwargs):
        kwargs.update(self.group_kwargs)
        super(_ParametersContext, self).register_alias(argument_name, options_list, **kwargs)

    def expand(self, argument_name, model_type, group_name=None, patches=None):
        # TODO:
        # two privates symbols are imported here. they should be made public or this utility class
        # should be moved into azure.cli.core
        from azure.cli.core.commands import _cli_extra_argument_registry
        from azure.cli.core.sdk.validators import get_complex_argument_processor
        from knack.introspection import extract_args_from_signature, option_descriptions

        if not patches:
            patches = dict()

        self.ignore(argument_name)

        # fetch the documentation for model parameters first. for models, which are the classes
        # derive from msrest.serialization.Model and used in the SDK API to carry parameters, the
        # document of their properties are attached to the classes instead of constructors.
        parameter_docs = option_descriptions(model_type)

        expanded_arguments = []
        for name, arg in extract_args_from_signature(model_type.__init__):
            if name in parameter_docs:
                arg.type.settings['help'] = parameter_docs[name]

            if group_name:
                arg.type.settings['arg_group'] = group_name

            if name in patches:
                patches[name](arg)

            _cli_extra_argument_registry[self._commmand][name] = arg
            expanded_arguments.append(name)

        self.argument(argument_name,
                      arg_type=ignore_type,
                      validator=get_complex_argument_processor(expanded_arguments,
                                                               argument_name,
                                                               model_type))
