# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for license information.
# --------------------------------------------------------------------------------------------


def load_arguments(self, command):
        from argcomplete.completers import FilesCompleter

        from azure.mgmt.resource.resources.models import DeploymentMode
        from azure.mgmt.resource.locks.models import LockLevel
        from azure.mgmt.resource.managedapplications.models import ApplicationLockLevel

        from azure.cli.core.commands.parameters import \
            (resource_group_name_type, tag_type, tags_type, get_resource_group_completion_list, no_wait_type, file_type,
             get_enum_type)
        from azure.cli.core.profiles import ResourceType

        from knack.arguments import ignore_type, CLIArgumentType

        from .custom import (get_policy_completion_list, get_policy_assignment_completion_list,
                             get_resource_types_completion_list, get_providers_completion_list)
        from ._validators import process_deployment_create_namespace, validate_lock_parameters

        # BASIC PARAMETER CONFIGURATION

        resource_name_type = CLIArgumentType(options_list=('--name', '-n'), help='The resource name. (Ex: myC)')
        resource_type_type = CLIArgumentType(help="The resource type (Ex: 'resC'). Can also accept namespace/type format (Ex: 'Microsoft.Provider/resC')")
        resource_namespace_type = CLIArgumentType(options_list=('--namespace',), completer=get_providers_completion_list,
                                                  help="Provider namespace (Ex: 'Microsoft.Provider')")
        resource_parent_type = CLIArgumentType(required=False, options_list=('--parent',),
                                               help="The parent path (Ex: 'resA/myA/resB/myB')")
        _PROVIDER_HELP_TEXT = 'the resource namespace, aka \'provider\''

        with self.argument_context('resource') as c:
            c.argument('no_wait', no_wait_type)
            c.argument('resource_id', ignore_type)
            c.argument('resource_name', resource_name_type, id_part='resource_name')
            c.argument('api_version', help='The api version of the resource (omit for latest)', required=False)
            c.argument('resource_provider_namespace', resource_namespace_type, id_part='resource_namespace')
            c.argument('resource_type', arg_type=resource_type_type, completer=get_resource_types_completion_list, id_part='resource_type')
            c.argument('parent_resource_path', resource_parent_type, id_part='resource_parent')
            c.argument('tag', tag_type)
            c.argument('tags', tags_type)

        with self.argument_context('resource list') as c:
            c.argument('name', resource_name_type)

        with self.argument_context('resource_move') as c:        
            c.argument('ids', nargs='+')

        with self.argument_context('resource invoke-action') as c:
            c.argument('action', help='The action that will be invoked on the specified resource')
            c.argument('request_body', help='JSON encoded parameter arguments for the action that will be passed along in the post request body. Use @{file} to load from a file.')

        with self.argument_context('resource create') as c:
            c.argument('resource_id', options_list=['--id'], help='Resource ID.', action=None)
            c.argument('properties', options_list=('--properties', '-p'), help='a JSON-formatted string containing resource properties')
            c.argument('is_full_object', action='store_true', help='Indicates that the properties object includes other options such as location, tags, sku, and/or plan.')

        with self.argument_context('provider') as c:
            c.argument('top', ignore_type)
            c.argument('resource_provider_namespace', options_list=('--namespace', '-n'), completer=get_providers_completion_list, help=_PROVIDER_HELP_TEXT)

        with self.argument_context('provider register') as c:
            c.argument('wait', action='store_true', help='wait for the registration to finish')

        with self.argument_context('provider unregister') as c:
            c.argument('wait', action='store_true', help='wait for unregistration to finish')

        with self.argument_context('provider operation') as c:
            c.argument('api_version', help="The api version of the 'Microsoft.Authorization/providerOperations' resource (omit for latest)")

        with self.argument_context('feature') as c:
            c.argument('resource_provider_namespace', options_list=('--namespace',), required=True, help=_PROVIDER_HELP_TEXT)
            c.argument('feature_name', options_list=('--name', '-n'), help='the feature name')

        with self.argument_context('feature list') as c:
            c.argument('resource_provider_namespace', options_list=('--namespace',), required=False, help=_PROVIDER_HELP_TEXT)

        existing_policy_definition_name_type = CLIArgumentType(options_list=('--name', '-n'), completer=get_policy_completion_list, help='The policy definition name')
        with self.argument_context('policy') as c:
            c.argument('resource_group_name', arg_type=resource_group_name_type, help='the resource group where the policy will be applied')

        with self.argument_context('policy definition', resource_type=ResourceType.MGMT_RESOURCE_POLICY) as c:
            c.argument('policy_definition_name', arg_type=existing_policy_definition_name_type)
            c.argument('rules', help='JSON formatted string or a path to a file with such content', type=file_type, completer=FilesCompleter())
            c.argument('display_name', help='display name of policy definition')
            c.argument('description', help='description of policy definition')
            c.argument('params', help='JSON formatted string or a path to a file or uri with parameter definitions', type=file_type, completer=FilesCompleter(), min_api='2016-12-01')


        with self.argument_context('policy definition create', resource_type=ResourceType.MGMT_RESOURCE_POLICY) as c:
            from azure.mgmt.resource.policy.models import PolicyMode
            c.argument('name', options_list=('--name', '-n'), help='name of the new policy definition')
            c.argument('mode', arg_type=get_enum_type(PolicyMode), options_list=('--mode', '-m'), help='mode of the new policy definition.', min_api='2016-12-01')


        with self.argument_context('policy assignment', resource_type=ResourceType.MGMT_RESOURCE_POLICY) as c:
            c.argument('name', options_list=('--name', '-n'), completer=get_policy_assignment_completion_list, help='name of the assignment')
            c.argument('scope', help='scope at which this policy assignment applies to, e.g., /subscriptions/0b1f6471-1bf0-4dda-aec3-111122223333, /subscriptions/0b1f6471-1bf0-4dda-aec3-111122223333/resourceGroups/myGroup, or /subscriptions/0b1f6471-1bf0-4dda-aec3-111122223333/resourceGroups/myGroup/providers/Microsoft.Compute/virtualMachines/myVM')
            c.argument('disable_scope_strict_match', action='store_true', help='include assignment either inhertied from parent scope or at child scope')
            c.argument('display_name', help='display name of the assignment')
            c.argument('policy', help='policy name or fully qualified id', completer=get_policy_completion_list)

        with self.argument_context('policy assignment create') as c:
            c.argument('name', options_list=('--name', '-n'), help='name of the new assignment')
            c.argument('params', options_list=('--params', '-p'), help='JSON formatted string or path to file with parameter values of policy rule', min_api='2016-12-01')

        with self.argument_context('group') as c:
            c.argument('tag', tag_type)
            c.argument('tags', tags_type)
            c.argument('resource_group_name', resource_group_name_type, options_list=('--name', '-n'))

        with self.argument_context('group deployment') as c:
            c.argument('resource_group_name', arg_type=resource_group_name_type, completer=get_resource_group_completion_list)
            c.argument('deployment_name', options_list=('--name', '-n'), required=True, help='The deployment name.')
            c.argument('template_file', completer=FilesCompleter(), type=file_type, help="a template file path in the file system")
            c.argument('template_uri', help='a uri to a remote template file')
            c.argument('mode', arg_type=get_enum_type(DeploymentMode), help='Incremental (only add resources to resource group) or Complete (remove extra resources from resource group)')
            c.argument('parameters', action='append', nargs='+', completer=FilesCompleter())

        with self.argument_context('group deployment create') as c:
            c.argument('deployment_name', options_list=('--name', '-n'), required=False,
                       validator=process_deployment_create_namespace, help='The deployment name. Default to template file base name')

        with self.argument_context('group deployment operation show') as c:
            c.argument('operation_ids', nargs='+', help='A list of operation ids to show')

        with self.argument_context('group export') as c:
            c.argument('include_comments', action='store_true')
            c.argument('include_parameter_default_value', action='store_true')

        with self.argument_context('group create') as c:
            c.argument('rg_name', options_list=('--name', '-n'), help='name of the new resource group', completer=None)

        with self.argument_context('tag') as c:
            c.argument('tag_name', options_list=('--name', '-n'))
            c.argument('tag_value', options_list=('--value',))

        with self.argument_context('lock') as c:
            c.argument('lock_name', options_list=('--name', '-n'), validator=validate_lock_parameters)
            c.argument('level', arg_type=get_enum_type(LockLevel), options_list=('--lock-type', '-t'))
            c.argument('parent_resource_path', resource_parent_type)
            c.argument('resource_provider_namespace', resource_namespace_type)
            c.argument('resource_type', arg_type=resource_type_type,
                                  completer=get_resource_types_completion_list,)
            c.argument('resource_name', options_list=('--resource-name'))
            c.argument('ids', nargs='+', options_list=('--ids'), help='One or more resource IDs (space delimited). If provided, no other "Resource Id" arguments should be specified.')

        with self.argument_context('managedapp') as c:
            c.argument('resource_group_name', arg_type=resource_group_name_type, help='the resource group of the managed application', id_part='resource_group')
            c.argument('application_name', options_list=('--name', '-n'), id_part='name')

        with self.argument_context('managedapp definition') as c:
            c.argument('resource_group_name', arg_type=resource_group_name_type, help='the resource group of the managed application definition', id_part='resource_group')
            c.argument('application_definition_name', options_list=('--name', '-n'), id_part='name')

        with self.argument_context('managedapp create') as c:
            c.argument('name', options_list=('--name', '-n'), help='name of the new managed application', completer=None)
            c.argument('location', help='the managed application location')
            c.argument('managedapp_definition_id', options_list=('--managedapp-definition-id', '-d'), help='the full qualified managed application definition id')
            c.argument('managedby_resource_group_id', options_list=('--managed-rg-id', '-m'), help='the resource group managed by the managed application')
            c.argument('parameters', help='JSON formatted string or a path to a file with such content', type=file_type)

        with self.argument_context('managedapp definition create') as c:
            c.argument('lock_level', arg_type=get_enum_type(ApplicationLockLevel))
            c.argument('authorizations', options_list=('--authorizations', '-a'), nargs='+', help="space separated authorization pairs in a format of <principalId>:<roleDefinitionId>")
            c.argument('createUiDefinition', options_list=('--create-ui-definition', '-c'), help='JSON formatted string or a path to a file with such content', type=file_type)
            c.argument('mainTemplate', options_list=('--main-template', '-t'), help='JSON formatted string or a path to a file with such content', type=file_type)
