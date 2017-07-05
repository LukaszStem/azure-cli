# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for license information.
# --------------------------------------------------------------------------------------------

from azure.cli.testsdk import ScenarioTest, JMESPathCheck, ResourceGroupPreparer


class RedisCacheTests(ScenarioTest):

    @ResourceGroupPreparer(name_prefix='cli_test_redis')
    def test_redis_cache(self, resource_group):

        name = self.create_random_name(prefix='redis', length=24)
        self.kwargs = {
            'rg': resource_group,
            'loc': 'WestUS',
            'name': name,
            'sku': 'basic',
            'size': 'C0'
        }

        self.cmd('az redis create -n {name} -g {rg} -l {loc} --sku {sku} --vm-size {size}')
        self.cmd('az redis show -n {name} -g {rg}', checks=[
            JMESPathCheck('name', self.kwargs['name']),
            JMESPathCheck('provisioningState', 'Creating')
        ])
        self.cmd('az redis list -g {rg}')
        self.cmd('az redis list-keys -n {name} -g {rg}')
