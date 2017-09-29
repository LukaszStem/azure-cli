# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for license information.
# --------------------------------------------------------------------------------------------

__version__ = "2.0.17+dev"

import configparser
import os
import sys

from knack.arguments import ignore_type, CLICommandArgument, ArgumentsContext
from knack.cli import CLI
from knack.commands import CLICommandsLoader, CLICommand, CommandGroup as KnackCommandGroup
from knack.completion import ARGCOMPLETE_ENV_NAME
from knack.introspection import extract_args_from_signature, extract_full_summary_from_signature
from knack.invocation import CommandInvoker
from knack.log import get_logger

import six

logger = get_logger(__name__)

CONFIRM_PARAM_NAME = 'yes'


def _expand_file_prefixed_files(args):
    def _load_file(path):
        from azure.cli.core.util import read_file_content
        if path == '-':
            content = sys.stdin.read()
        else:
            content = read_file_content(os.path.expanduser(path), allow_binary=True)

        return content[0:-1] if content and content[-1] == '\n' else content

    def _maybe_load_file(arg):
        ix = arg.find('@')
        if ix == -1:  # no @ found
            return arg

        poss_file = arg[ix + 1:]
        if not poss_file:  # if nothing after @ then it can't be a file
            return arg
        elif ix == 0:
            return _load_file(poss_file)

        # if @ not at the start it can't be a file
        return arg

    def _expand_file_prefix(arg):
        arg_split = arg.split('=', 1)
        try:
            return '='.join([arg_split[0], _maybe_load_file(arg_split[1])])
        except IndexError:
            return _maybe_load_file(arg_split[0])

    return list([_expand_file_prefix(arg) for arg in args])


def _pre_command_table_create(cli_ctx, args):

    cli_ctx.refresh_request_id()
    return _expand_file_prefixed_files(args)


def _explode_list_args(args):
    '''Iterate through each attribute member of args and create a copy with
    the IterateValues 'flattened' to only contain a single value

    Ex.
        { a1:'x', a2:IterateValue(['y', 'z']) } => [{ a1:'x', a2:'y'),{ a1:'x', a2:'z'}]
    '''
    from azure.cli.core.commands.validators import IterateValue
    import argparse
    list_args = {argname: argvalue for argname, argvalue in vars(args).items()
                 if isinstance(argvalue, IterateValue)}
    if not list_args:
        yield args
    else:
        values = list(zip(*list_args.values()))
        for key in list_args:
            delattr(args, key)

        for value in values:
            new_ns = argparse.Namespace(**vars(args))
            for key_index, key in enumerate(list_args.keys()):
                setattr(new_ns, key, value[key_index])
            yield new_ns

class AzCli(CLI):

    def __init__(self, **kwargs):
        super(AzCli, self).__init__(**kwargs)

        from azure.cli.core.commands.arm import add_id_parameters
        from azure.cli.core.cloud import get_active_cloud
        import azure.cli.core.commands.progress as progress
        from azure.cli.core.extensions import register_extensions
        from azure.cli.core._profile import Profile
        from azure.cli.core._session import ACCOUNT, CONFIG, SESSION

        import knack.events as events

        self.data['headers'] = {}
        self.data['command'] = 'unknown'
        self.data['completer_active'] = ARGCOMPLETE_ENV_NAME in os.environ
        self.data['query_active'] = False

        azure_folder = self.config.config_dir
        ACCOUNT.load(os.path.join(azure_folder, 'azureProfile.json'))
        CONFIG.load(os.path.join(azure_folder, 'az.json'))
        SESSION.load(os.path.join(azure_folder, 'az.sess'), max_age=3600)
        self.cloud = get_active_cloud(self)
        logger.debug('Current cloud config:\n%s', str(self.cloud.name))

        self.progress_controller = progress.ProgressHook()

        register_extensions(self)
        self.register_event(events.EVENT_INVOKER_POST_CMD_TBL_CREATE, add_id_parameters)
        # TODO: Doesn't work because args get copied
        # self.register_event(events.EVENT_INVOKER_PRE_CMD_TBL_CREATE, _pre_command_table_create)

    def refresh_request_id(self):
        """Assign a new random GUID as x-ms-client-request-id

        The method must be invoked before each command execution in order to ensure
        unique client-side request ID is generated.
        """
        import uuid
        self.data['headers']['x-ms-client-request-id'] = str(uuid.uuid1())

    def get_progress_controller(self, det=False):
        import azure.cli.core.commands.progress as progress
        self.progress_controller.init_progress(progress.get_progress_view(det))
        return self.progress_controller

    def get_cli_version(cli):
        from azure.cli.core.util import get_az_version_string
        return get_az_version_string(cli.output)


class AzCliCommand(CLICommand):

    def __init__(self, cli_ctx, name, handler, description=None, table_transformer=None,
                 arguments_loader=None, description_loader=None,
                 formatter_class=None, deprecate_info=None, validator=None, **kwargs):
        super(AzCliCommand, self).__init__(cli_ctx, name, handler, description=description,
                                           table_transformer=table_transformer, arguments_loader=arguments_loader,
                                           description_loader=description_loader, formatter_class=formatter_class,
                                           deprecate_info=deprecate_info, validator=validator, **kwargs)
        self.command_source = None
        self.no_wait_param = kwargs.get('no_wait_param', None)
        self.exception_handler = kwargs.get('exception_handler', None)

    def _resolve_default_value_from_cfg_file(self, arg, overrides):
        from azure.cli.core._config import DEFAULTS_SECTION

        if not hasattr(arg.type, 'required_tooling'):
            required = arg.type.settings.get('required', False)
            setattr(arg.type, 'required_tooling', required)
        if 'configured_default' in overrides.settings:
            def_config = overrides.settings.pop('configured_default', None)
            setattr(arg.type, 'default_name_tooling', def_config)
            # same blunt mechanism like we handled id-parts, for create command, no name default
            if (self.name.split()[-1] == 'create' and overrides.settings.get('metavar', None) == 'NAME'):
                return
            setattr(arg.type, 'configured_default_applied', True)
            config_value = self.cli_ctx.config.get(DEFAULTS_SECTION, def_config, None)
            if config_value:
                logger.warning("Using default '%s' for arg %s", config_value, arg.name)
                overrides.settings['default'] = config_value
                overrides.settings['required'] = False


    def update_argument(self, param_name, argtype):
        arg = self.arguments[param_name]
        self._resolve_default_value_from_cfg_file(arg, argtype)
        arg.type.update(other=argtype)


    def __call__(self, *args, **kwargs):
        if self.command_source and isinstance(self.command_source, ExtensionCommandSource) and\
           self.command_source.overrides_command:
            logger.warning(self.command_source.get_command_warn_msg())
        if self.deprecate_info is not None:
            text = 'This command is deprecating and will be removed in future releases.'
            if self.deprecate_info:
                text += " Use '{}' instead.".format(self.deprecate_info)
            logger.warning(text)
        return self.handler(*args, **kwargs)


class MainCommandsLoader(CLICommandsLoader):

    def __init__(self, cli_ctx=None):
        import knack.events as events
        super(MainCommandsLoader, self).__init__(cli_ctx)
        self.loaders = []

    def load_command_table(self, args):
        from azure.cli.core.commands import get_command_table
        from azure.cli.core.extension import (get_extension_names, get_extension_path,
                                              get_extension_modname, EXTENSIONS_MOD_PREFIX)

        self.command_table = get_command_table(self, args)

        def _get_command_table_from_extensions():
            extensions = get_extension_names()
            if extensions:
                logger.debug("Found {} extensions: {}".format(len(extensions), extensions))
                for ext_name in extensions:
                    ext_dir = get_extension_path(ext_name)
                    sys.path.append(ext_dir)
                    try:
                        ext_mod = get_extension_modname(ext_dir=ext_dir)
                        # Add to the map. This needs to happen before we load commands as registering a command
                        # from an extension requires this map to be up-to-date.
                        mod_to_ext_map[ext_mod] = ext_name
                        start_time = timeit.default_timer()
                        import_module(ext_mod).load_commands()
                        elapsed_time = timeit.default_timer() - start_time
                        logger.debug("Loaded extension '%s' in %.3f seconds.", ext_name, elapsed_time)
                    except Exception:  # pylint: disable=broad-except
                        logger.warning("Unable to load extension '%s'. Use --debug for more information.", ext_name)
                        logger.debug(traceback.format_exc())

        try:
            # We always load extensions even if the appropriate module has been loaded
            # as an extension could override the commands already loaded.
            _get_command_table_from_extensions()
        except Exception:  # pylint: disable=broad-except
            logger.warning("Unable to load extensions. Use --debug for more information.")
            logger.debug(traceback.format_exc())

        return self.command_table

    def load_arguments(self, command):
        from azure.cli.core.commands.parameters import resource_group_name_type, location_type, deployment_name_type
        from knack.arguments import ignore_type

        for loader in self.loaders:
            loader.load_arguments(command)
            self.argument_registry.arguments.update(loader.argument_registry.arguments)

        with ArgumentsContext(self, '') as c:
            c.argument('resource_group_name', resource_group_name_type)
            c.argument('location', location_type)
            c.argument('deployment_name', deployment_name_type)
            c.argument('cli_ctx', ignore_type, default=self.cli_ctx)

        super(MainCommandsLoader, self).load_arguments(command)


class AzCommandsLoader(CLICommandsLoader):

    def __init__(self, cli_ctx=None, resource_type=None):
        from azure.cli.core.profiles import PROFILE_TYPE
        super(AzCommandsLoader, self).__init__(cli_ctx=cli_ctx, command_cls=AzCliCommand)
        self.module_name = __name__
        self.resource_type = resource_type or PROFILE_TYPE
        self.max_api = 'latest'
        self.min_api = None
        self._command_module_map = {}
        self._mod_to_ext_map = {}

    def load_command_table(self, args):
        if self.supported_api_version():
            return super().load_command_table(args)

    def load_arguments(self, command):
        if self.supported_api_version():
            return super().load_arguments(command)

    def supported_api_version(self, resource_type=None, min_api=None, max_api=None):
        from azure.cli.core.profiles import supported_api_version
        return supported_api_version(
            cli_ctx=self.cli_ctx,
            resource_type=resource_type or self.resource_type,
            min_api=min_api or self.min_api,
            max_api=max_api or self.max_api)

    def command_group(self, group_name, command_type=None, **kwargs):
        from azure.cli.core.sdk.util import _CommandGroup
        merged_kwargs = command_type.settings.copy()
        merged_kwargs.update(kwargs)
        return _CommandGroup(self.module_name, self, group_name, command_type, **merged_kwargs)

    def argument_context(self, scope, **kwargs):
        from azure.cli.core.sdk.util import _ParametersContext
        return _ParametersContext(self, scope, **kwargs)

    def _cli_command(self, name, operation=None, handler=None, **kwargs):
        from azure.cli.core.extension import EXTENSIONS_MOD_PREFIX

        self.command_table[name] = self._create_command(self.module_name, name, operation=operation, handler=handler, **kwargs)

        # Set the command source as we have the current command table and are about to add the command
        if self.module_name and self.module_name.startswith(EXTENSIONS_MOD_PREFIX):
            from azure.cli.core.commands import ExtensionCommandSource
            ext_mod = self.module_name.split('.')[0]
            self.command_table[name].command_source = ExtensionCommandSource(
                extension_name=self._mod_to_ext_map.get(ext_mod, None))
            if name in self.command_table:
                self.command_table[name].command_source.overrides_command = True
        else:
            self.command_table[name].command_source = None

    def _create_command(self, module_name, name, operation=None, handler=None, **kwargs):  # pylint: disable=unused-argument

        if operation and not isinstance(operation, six.string_types):
            raise TypeError("Operation must be a string. Got '{}'".format(operation))
        if handler and not callable(handler):
            raise TypeError("Handler must be a callable. Got '{}'".format(operation))
        if bool(operation) == bool(handler):
            raise TypeError("Must specify exactly one of either 'operation' or 'handler'")

        name = ' '.join(name.split())

        confirmation = kwargs.get('confirmation', False)
        no_wait_param = kwargs.get('no_wait_param', None)
        client_factory = kwargs.get('client_factory', None)

        def _command_handler(command_args):
            if confirmation \
                and not command_args.get(CONFIRM_PARAM_NAME) \
                and not self.cli_ctx.config.getboolean('core', 'disable_confirm_prompt', fallback=False) \
                    and not AzCommandsLoader.user_confirmed(confirmation, command_args):
                from knack.events import EVENT_COMMAND_CANCELLED
                from knack.util import CLIError

                self.cli_ctx.raise_event(EVENT_COMMAND_CANCELLED, command=name, command_args=command_args)
                raise CLIError('Operation cancelled.')
            op = self._get_op_handler(operation)
            client = client_factory(self.cli_ctx, command_args) if client_factory else None
            result = op(client, **command_args) if client else op(**command_args)
            return result

        def arguments_loader():
            op_handler = handler or self._get_op_handler(operation)
            cmd_args = list(extract_args_from_signature(op_handler))
            # this was previously stored in "extract_args_from_signature" but that no longer works so it is being
            # relocated here.
            if no_wait_param:
                cmd_args.append((no_wait_param,
                    CLICommandArgument(no_wait_param, options_list=['--no-wait'], action='store_true',
                                       help='Do not wait for the long running operation to finish.')))
            if confirmation:
                cmd_args.append((CONFIRM_PARAM_NAME,
                    CLICommandArgument(CONFIRM_PARAM_NAME, options_list=['--yes','-y'], action='store_true',
                                       help='Do not prompt for confirmation.')))
            return cmd_args


        def description_loader():
            op_handler = handler or self._get_op_handler(operation)
            return extract_full_summary_from_signature(op_handler)

        kwargs['arguments_loader'] = arguments_loader
        kwargs['description_loader'] = description_loader

        return self.command_cls(self.cli_ctx, name, handler or _command_handler, **kwargs)

    def _get_op_handler(self, operation):
        """ Import and load the operation handler """
        # Patch the unversioned sdk path to include the appropriate API version for the
        # resource type in question.
        from importlib import import_module
        import types

        from azure.cli.core.profiles import ResourceType
        from azure.cli.core.profiles._shared import get_versioned_sdk_path

        for rt in ResourceType:
            if operation.startswith(rt.import_prefix):
                operation = operation.replace(rt.import_prefix,
                                              get_versioned_sdk_path(self.cli_ctx.cloud.profile, rt))

        try:
            mod_to_import, attr_path = operation.split('#')
            op = import_module(mod_to_import)
            for part in attr_path.split('.'):
                op = getattr(op, part)
            if isinstance(op, types.FunctionType):
                return op
            return six.get_method_function(op)
        except (ValueError, AttributeError):
            raise ValueError("The operation '{}' is invalid.".format(operation))


class AzCliCommandInvoker(CommandInvoker):

    def execute(self, argv):
        import azure.cli.core.telemetry as telemetry
        import knack.events as events
        from knack.util import CommandResultItem, todict, CLIError
        from msrest.paging import Paged


        # TODO: Can't simply be invoked as an event because args are transformed
        args = _pre_command_table_create(self.cli_ctx, argv)

        self.cli_ctx.raise_event(events.EVENT_INVOKER_PRE_CMD_TBL_CREATE, args=args)
        cmd_tbl = self.commands_loader.load_command_table(args)
        command = self._rudimentary_get_command(args)
        self.commands_loader.load_arguments(command)
        try:
            cmd_tbl = {command: self.commands_loader.command_table[command]} if command else cmd_tbl
        except KeyError:
            pass
        self.cli_ctx.raise_event(events.EVENT_INVOKER_POST_CMD_TBL_CREATE, cmd_tbl=cmd_tbl)
        self.parser.load_command_table(cmd_tbl)
        self.cli_ctx.raise_event(events.EVENT_INVOKER_CMD_TBL_LOADED, cmd_tbl=cmd_tbl, parser=self.parser)

        if not args:
            self.cli_ctx.completion.enable_autocomplete(self.parser)
            subparser = self.parser.subparsers[tuple()]
            self.help.show_welcome(subparser)

            # TODO: No event in base with which to target
            telemetry.set_command_details('az')
            telemetry.set_success(summary='welcome')
            return None

        if args[0].lower() == 'help':
            args[0] = '--help'

        self.cli_ctx.completion.enable_autocomplete(self.parser)

        self.cli_ctx.raise_event(events.EVENT_INVOKER_PRE_PARSE_ARGS, args=args)
        parsed_args = self.parser.parse_args(args)
        self.cli_ctx.raise_event(events.EVENT_INVOKER_POST_PARSE_ARGS, command=parsed_args.command, args=parsed_args)


        # TODO: This fundamentally alters the way Knack.invocation works here. Cannot be customized
        # with an event. Would need to be customized via inheritance.
        results = []
        for expanded_arg in _explode_list_args(parsed_args):

            self._validation(expanded_arg)

            self.data['command'] = expanded_arg.command

            params = self._filter_params(expanded_arg)

            telemetry.set_command_details(self.data['command'],
                                          self.data['output'],
                                          [p for p in argv if p.startswith('-')])

            try:
                from azure.cli.core.commands import _is_paged, _is_poller, LongRunningOperation
                cmd = expanded_arg.func
                result = cmd(params)
                no_wait_param = cmd.no_wait_param
                if no_wait_param and getattr(expanded_arg, no_wait_param, False):
                    result = None
                elif _is_poller(result):
                    result = LongRunningOperation(self.cli_ctx, 'Starting {}'.format(cmd.name))(result)
                elif _is_paged(result):
                    result = todict(list(result))
                else:
                    result = todict(result)

                results.append(result)
            except Exception as ex:  # pylint: disable=broad-except
                from azure.cli.core.commands import _check_rp_not_registered_err, _register_rp
                rp = _check_rp_not_registered_err(ex)
                if rp:
                    _register_rp(rp)
                    continue  # retry
                if cmd.exception_handler:
                    cmd.exception_handler(ex)
                    return
                else:
                    six.reraise(*sys.exc_info())

        if results and len(results) == 1:
            results = results[0]

        event_data = {'result': results}
        self.cli_ctx.raise_event(events.EVENT_INVOKER_TRANSFORM_RESULT, event_data=event_data)
        self.cli_ctx.raise_event(events.EVENT_INVOKER_FILTER_RESULT, event_data=event_data)

        return CommandResultItem(event_data['result'],
                                 table_transformer=cmd_tbl[parsed_args.command].table_transformer,
                                 is_query_active=self.data['query_active'])
