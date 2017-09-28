# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for license information.
# --------------------------------------------------------------------------------------------

from collections import OrderedDict

from azure.cli.core.util import empty_on_404
from azure.cli.core.profiles import ResourceType, get_api_version
from azure.cli.core.sdk.util import CliCommandType

from azure.cli.command_modules.resource._client_factory import \
    (_resource_client_factory, cf_resource_groups, cf_providers, cf_features, cf_tags, cf_deployments,
     cf_deployment_operations, cf_policy_definitions, cf_resource_links, cf_resource_managedapplications,
     cf_resource_managedappdefinitions)


def load_command_table(self, args):
    from azure.cli.core.commands.arm import \
        (handle_long_running_operation_exception, deployment_validate_table_format)

    # Resource group commands
    def transform_resource_group_list(result):
        return [OrderedDict([('Name', r['name']), ('Location', r['location']), ('Status', r['properties']['provisioningState'])]) for r in result]

    resource_custom = CliCommandType(
        operations_tmpl='azure.cli.command_modules.resource.custom#CustomResourceOperations.{}',
        client_factory=None
    )

    resource_group_sdk = CliCommandType(
        operations_tmpl='azure.mgmt.resource.resources.operations.resource_groups_operations#ResourceGroupsOperations.{}',
        client_factory=cf_resource_groups
    )

    resource_provider_sdk = CliCommandType(
        operations_tmpl='azure.mgmt.resource.resources.operations.providers_operations#ProvidersOperations.{}',
        client_factory=cf_providers
    )

    resource_feature_sdk = CliCommandType(
        operations_tmpl='azure.mgmt.resource.features.operations.features_operations#FeaturesOperations.{}',
        client_factory=cf_features
    )

    resource_tag_sdk = CliCommandType(
        operations_tmpl='azure.mgmt.resource.resources.operations.tags_operations#TagsOperations.{}',
        client_factory=cf_tags
    )

    resource_deployment_sdk = CliCommandType(
        operations_tmpl='azure.mgmt.resource.resources.operations.deployments_operations#DeploymentsOperations.{}',
        client_factory=cf_deployments
    )

    resource_deployment_operation_sdk = CliCommandType(
        operations_tmpl='azure.mgmt.resource.resources.operations.deployments_operations#DeploymentsOperations.{}',
        client_factory=cf_deployment_operations
    )

    resource_policy_definitions_sdk = CliCommandType(
        operations_tmpl='azure.mgmt.resource.policy.operations#PolicyDefinitionsOperations.{}',
        client_factory=cf_policy_definitions
    )

    resource_lock_sdk = CliCommandType(operations_tmpl='azure.mgmt.resource.policy.operations#PolicyDefinitionsOperations.{}')

    resource_link_sdk = CliCommandType(
        operations_tmpl='azure.mgmt.resource.links.operations#ResourceLinksOperations.{}',
        client_factory=cf_resource_links
    )

    resource_managedapp_sdk = CliCommandType(
        operations_tmpl='azure.mgmt.resource.managedapplications.operations#AppliancesOperations.{}',
        client_factory=cf_resource_managedapplications
    )

    resource_managedapp_def_sdk = CliCommandType(
        operations_tmpl='azure.mgmt.resource.managedapplications.operations#ApplianceDefinitionsOperations.{}',
        client_factory=cf_resource_managedappdefinitions
    )

    with self.command_group('group', resource_group_sdk) as g:
        g.command('delete', 'delete', no_wait_param='raw', confirmation=True)
        # self.cli_generic_wait_command(__name__, 'group wait', 'azure.mgmt.resource.resources.operations.resource_groups_operations#ResourceGroupsOperations.get', cf_resource_groups)
        g.command('show', 'get', exception_handler=empty_on_404)
        g.command('exists', 'check_existence')
        g.command('list', 'list_resource_groups', resource_custom, table_transformer=transform_resource_group_list)
        g.command('create', 'create_resource_group', resource_custom)
        g.command('export', 'export_group_as_template', resource_custom)
        g.generic_update_command('update')

    # Resource commands

    def transform_resource_list(result):
        transformed = []
        for r in result:
            res = OrderedDict([('Name', r['name']), ('ResourceGroup', r['resourceGroup']), ('Location', r['location']), ('Type', r['type'])])
            try:
                res['Status'] = r['properties']['provisioningStatus']
            except TypeError:
                res['Status'] = ' '
            transformed.append(res)
        return transformed

    with self.command_group('resource', resource_custom) as g:
        g.command('create', 'create_resource')
        g.command('delete', 'delete_resource')
        g.command('show', 'show_resource', exception_handler=empty_on_404)
        g.command('list', 'list_resources', table_transformer=transform_resource_list)
        g.command('tag', 'tag_resource')
        g.command('move', 'move_resource')
        #self.cli_generic_update_command(__name__, 'resource update',
        #                                'azure.cli.command_modules.resource.custom#show_resource',
        #                                'azure.cli.command_modules.resource.custom#update_resource')

    # Resource provider commands
    with self.command_group('provider', resource_custom) as g:
        g.command('list', 'list', resource_provider_sdk)
        g.command('show', 'get', resource_provider_sdk, exception_handler=empty_on_404)
        g.command('register', 'register_provider')
        g.command('unregister', 'unregister_provider')
        g.command('operation list', 'list_provider_operations')
        g.command('operation show', 'show_provider_operations')

    # Resource feature commands
    if self.supported_api_version(min_api='2017-05-10'):
        with self.command_group('feature', resource_feature_sdk) as g:
            g.command('list', 'list_features', resource_custom, client_factory=cf_features)
            g.command('show', 'get', exception_handler=empty_on_404)
            g.command('register', 'register')

    # Tag commands
    with self.command_group('tag', resource_tag_sdk) as g:
        g.command('list', 'list')
        g.command('create', 'create_or_update')
        g.command('delete', 'delete')
        g.command('add-value', 'create_or_update_value')
        g.command('remove-value', 'delete_value')

    # Resource group deployment commands
    def transform_deployments_list(result):
        sort_list = sorted(result, key=lambda deployment: deployment['properties']['timestamp'])
        return [OrderedDict([('Name', r['name']), ('Timestamp', r['properties']['timestamp']), ('State', r['properties']['provisioningState'])]) for r in sort_list]

    with self.command_group('group deployment', resource_deployment_sdk) as g:
        g.command('create', 'deploy_arm_template', resource_custom, no_wait_param='no_wait', exception_handler=handle_long_running_operation_exception)
        # self.cli_generic_wait_command(__name__, 'group deployment wait', 'azure.mgmt.resource.resources.operations.deployments_operations#DeploymentsOperations.get', cf_deployments)
        if self.supported_api_version(min_api='2017-05-10'):
            g.command('list', 'list_by_resource_group', table_transformer=transform_deployments_list)
        else:
            g.command('list', 'list', table_transformer=transform_deployments_list)
        g.command('show', 'get', exception_handler=empty_on_404)
        g.command('delete', 'delete')
        g.command('validate', 'validate_arm_template', resource_custom, table_transformer=deployment_validate_table_format)
        g.command('export', 'export_deployment_as_template', resource_custom)

    with self.command_group('group deployment operation', resource_deployment_operation_sdk) as g:
        # Resource group deployment operations commands
        g.command('list', 'list')
        g.command('show', 'get_deployment_operations', resource_custom, client_factory=cf_deployment_operations, exception_handler=empty_on_404)

    with self.command_group('policy assignment', resource_custom) as g:
        g.command('create', 'create_policy_assignment')
        g.command('delete', 'delete_policy_assignment')
        g.command('list', 'list_policy_assignment')
        g.command('show', 'show_policy_assignment', exception_handler=empty_on_404)

    with self.command_group('policy definition', resource_policy_definitions_sdk) as g:
        g.command('create', 'create_policy_definition', arg_type=resource_custom)
        g.command('delete', 'delete')
        g.command('list', 'list')
        g.command('show', 'get', exception_handler=empty_on_404)
        g.command('update', 'update_policy_definition', arg_type=resource_custom)

    with self.command_group('lock', resource_custom) as g:
        g.command('create', 'create_lock')
        g.command('delete', 'delete_lock')
        g.command('list', 'list_locks')
        g.command('show', 'get_lock', exception_handler=empty_on_404)
        g.command('update', 'update_lock')

    with self.command_group('resource link', resource_custom) as g:
        g.command('create', 'create_resource_link')
        g.command('delete', 'delete')
        g.command('show', 'get', exception_handler=empty_on_404)
        g.command('list', 'list_resource_links')
        g.command('update', 'update_resource_link')

    if self.supported_api_version(min_api='2017-05-10'):
        with self.command_group('managedapp', resource_custom) as g:
            g.command('create', 'create_appliance')
            g.command('delete', 'delete', resource_managedapp_sdk)
            g.command('show', 'show_appliance', exception_handler=empty_on_404)
            g.command('list', 'list_appliances')

        with self.command_group('managedapp definition', resource_custom) as g:
            g.command('create', 'create_appliancedefinition')
            g.command('delete', 'delete', resource_managedapp_def_sdk)
            g.command('show', 'show_appliancedefinition')
            g.command('list', 'list_by_resource_group', resource_managedapp_def_sdk, exception_handler=empty_on_404)
