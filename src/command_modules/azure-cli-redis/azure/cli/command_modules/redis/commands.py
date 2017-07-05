# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for license information.
# --------------------------------------------------------------------------------------------

from azure.cli.core.sdk.util import CliCommandType

from azure.cli.command_modules.redis._client_factory import cf_redis, cf_patch_schedules
from azure.cli.command_modules.redis.custom import wrong_vmsize_argument_exception_handler, CustomRedisOperations


def load_command_table(self, args):

    redis_sdk = CliCommandType(
        operations_tmpl='azure.mgmt.redis.operations.redis_operations#RedisOperations.{}',
        client_factory=cf_redis)

    redis_custom = CliCommandType(
        operations_tmpl='azure.cli.command_modules.redis.custom#CustomRedisOperations.{}',
        client_factory=cf_redis)

    redis_patch = CliCommandType(
        operations_tmpl='azure.mgmt.redis.operations.patch_schedules_operations#PatchSchedulesOperations.{}',
        client_factory=cf_patch_schedules)

    with self.command_group('redis', redis_sdk) as g:
        g.command('create', 'cli_redis_create', redis_custom,  exception_handler=wrong_vmsize_argument_exception_handler)
        g.command('delete', 'delete')
        g.command('export', 'cli_redis_export', redis_custom)
        g.command('force-reboot', 'force_reboot')
        g.command('import-method', 'cli_redis_import_method', redis_custom)
        g.command('list', 'list_by_resource_group')
        g.command('list-all', 'list')
        g.command('list-keys', 'list_keys')
        g.command('regenerate-keys', 'regenerate_key')
        g.command('show', 'get')
        g.command('update-settings', 'cli_redis_update_settings', redis_custom)

        #g.generic_update_command('update', 'get', 'create_or_update', redis_sdk,
        #                          custom_function_op=(redis_custom, 'cli_redis_update'),
        #                          exception_handler=wrong_vmsize_argument_exception_handler)

    with self.command_group('redis patch-schedule', redis_patch) as g:
        g.command('set', 'create_or_update')
        g.command('delete', 'delete')
        g.command('patch-schedule show', 'get')
