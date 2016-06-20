# -*- encoding: utf-8 -*-
# pylint: disable=no-self-use
"""Test class for Organization CLI

@Requirement: Organization

@CaseAutomation: Automated

@CaseLevel: Acceptance

@CaseComponent: CLI

@TestType: Functional

@CaseImportance: High

@Upstream: No
"""
import random

from fauxfactory import gen_string
from itertools import cycle
from robottelo.cleanup import capsule_cleanup, org_cleanup
from robottelo.cli.base import CLIReturnCodeError
from robottelo.cli.factory import (
    make_compute_resource,
    make_domain,
    make_hostgroup,
    make_lifecycle_environment,
    make_medium,
    make_org,
    make_proxy,
    make_subnet,
    make_template,
    make_user,
)
from robottelo.cli.lifecycleenvironment import LifecycleEnvironment
from robottelo.cli.org import Org
from robottelo.config import settings
from robottelo.constants import FOREMAN_PROVIDERS
from robottelo.datafactory import (
    datacheck,
    invalid_values_list,
    valid_data_list,
    valid_org_names_list,
)
from robottelo.decorators import (
    run_only_on,
    tier1,
    tier2,
)
from robottelo.test import CLITestCase


@datacheck
def valid_labels_list():
    """Random simpler data for positive creation

    Use this when name and label must match. Labels cannot contain the same
    data type as names, so this is a bit limited compared to other tests.
    Label cannot contain characters other than ascii alpha numerals, '_', '-'.
    """
    return [
        gen_string('alpha'),
        gen_string('alphanumeric'),
        gen_string('numeric'),
        '{0}-{1}'.format(gen_string('alpha', 5), gen_string('alpha', 5)),
        '{0}_{1}'.format(gen_string('alpha', 5), gen_string('alpha', 5)),
    ]


class OrganizationTestCase(CLITestCase):
    """Tests for Organizations via Hammer CLI"""

    # Tests for issues

    # This Bugzilla bug is private. It is impossible to fetch info about it.
    @tier1
    def test_verify_bugzilla_1078866(self):
        """hammer organization <info,list> --help types information
        doubled

        @id: 7938bcc4-7107-40b0-bb88-6288ebec0dcd

        @Assert: no duplicated lines in usage message
        """
        # org list --help:
        result = Org.list({'help': True})
        # get list of lines and check they all are unique
        lines = [line['message'] for line in result]
        self.assertEqual(len(set(lines)), len(lines))

        # org info --help:info returns more lines (obviously), ignore exception
        result = Org.info({'help': True})

        # get list of lines and check they all are unique
        lines = [line for line in result['options']]
        self.assertEqual(len(set(lines)), len(lines))

    # CRUD

    @tier1
    def test_positive_create_with_name(self):
        """Create organization with valid name only

        @id: 35840da7-668e-4f78-990a-738aa688d586

        @assert: organization is created and has appropriate name
        """
        for name in valid_org_names_list():
            with self.subTest(name):
                org = make_org({'name': name})
                self.assertEqual(org['name'], name)

    @tier1
    def test_positive_create_with_matching_name_label(self):
        """Create organization with valid matching name and label only

        @id: aea551de-145b-4894-b4fb-65878ff1f101

        @assert: organization is created, label matches name
        """
        for test_data in valid_labels_list():
            with self.subTest(test_data):
                org = make_org({
                    'label': test_data,
                    'name': test_data,
                })
                self.assertEqual(org['name'], org['label'])

    @tier1
    def test_positive_create_with_unmatched_name_label(self):
        """Create organization with valid unmatching name and label only

        @id: a4730b09-1bd7-4b00-a7ee-76080a916ea8

        @assert: organization is created, label does not match name
        """
        for name in valid_org_names_list():
            with self.subTest(name):
                label = gen_string('alpha')
                org = make_org({
                    'label': label,
                    'name': name,
                })
                self.assertNotEqual(org['name'], org['label'])
                self.assertEqual(org['name'], name)
                self.assertEqual(org['label'], label)

    @tier1
    def test_positive_create_with_name_description(self):
        """Create organization with valid name and description only

        @id: b28c95ba-918e-47fe-8681-61e05b8fe2ea

        @assert: organization is created
        """
        for name, desc in zip(valid_org_names_list(), valid_data_list()):
            with self.subTest(name + desc):
                org = make_org({
                    'description': desc,
                    'name': name,
                })
                self.assertEqual(org['name'], name)
                self.assertEqual(org['description'], desc)

    @tier1
    def test_positive_create_with_name_label_description(self):
        """Create organization with valid name, label and description

        @id: 9a1f70f6-fb5f-4b23-9f7e-b0973fbbba30

        @assert: organization is created
        """
        for description in valid_data_list():
            with self.subTest(description):
                label = gen_string('alpha')
                name = gen_string('alpha')
                org = make_org({
                    'description': description,
                    'label': label,
                    'name': name,
                })
                self.assertEqual(org['description'], description)
                self.assertEqual(org['label'], label)
                self.assertEqual(org['name'], name)

    @tier1
    def test_positive_list(self):
        """Check if Org can be listed

        @id: bdd26bb3-e3d2-4a5c-8be7-fb12c1114ccc

        @Assert: Org is listed
        """
        org = make_org()
        result_list = Org.list({
            'search': 'name=%s' % org['name']})
        self.assertTrue(len(result_list) > 0)
        self.assertEqual(result_list[0]['name'], org['name'])

    @run_only_on('sat')
    @tier2
    def test_positive_add_subnet_by_name(self):
        """Add a subnet to organization by its name

        @id: 1f464eba-d024-4f37-87c2-5cfff1ac1e23

        @Assert: Subnet is added to the org

        @CaseLevel: Integration
        """
        for name in valid_data_list():
            with self.subTest(name):
                org = make_org()
                new_subnet = make_subnet({'name': name})
                Org.add_subnet({
                    'name': org['name'],
                    'subnet': new_subnet['name'],
                })
                org = Org.info({'id': org['id']})
                self.assertIn(name, org['subnets'][0])

    @run_only_on('sat')
    @tier2
    def test_positive_add_subnet_by_id(self):
        """Add a subnet to organization by its ID

        @id: f65e4264-4aad-42f8-b74f-933741d9f7ab

        @assert: Subnet is added to the org

        @CaseLevel: Integration
        """
        org = make_org()
        new_subnet = make_subnet()
        Org.add_subnet({
            'name': org['name'],
            'subnet-id': new_subnet['id'],
        })
        org = Org.info({'id': org['id']})
        self.assertIn(new_subnet['name'], org['subnets'][0])

    @run_only_on('sat')
    @tier2
    def test_positive_remove_subnet_by_name(self):
        """Remove a subnet from organization by its name

        @id: adb5310b-76c5-4aca-8220-fdf0fe605cb0

        @Assert: Subnet is removed from the org

        @CaseLevel: Integration
        """
        org = make_org()
        subnet = make_subnet()
        Org.add_subnet({
            'name': org['name'],
            'subnet': subnet['name'],
        })
        org = Org.info({'id': org['id']})
        self.assertEqual(len(org['subnets']), 1)
        self.assertIn(subnet['name'], org['subnets'][0])
        Org.remove_subnet({
            'name': org['name'],
            'subnet': subnet['name'],
        })
        org = Org.info({'id': org['id']})
        self.assertEqual(len(org['subnets']), 0)

    @run_only_on('sat')
    @tier2
    def test_positive_remove_subnet_by_id(self):
        """Remove a subnet from organization by its ID

        @id: 4868ef18-983a-48b4-940a-e1b55f01f0b6

        @Assert: Subnet is removed from the org

        @CaseLevel: Integration
        """
        org = make_org()
        subnet = make_subnet()
        Org.add_subnet({
            'name': org['name'],
            'subnet': subnet['name'],
        })
        org = Org.info({'id': org['id']})
        self.assertEqual(len(org['subnets']), 1)
        self.assertIn(subnet['name'], org['subnets'][0])
        Org.remove_subnet({
            'name': org['name'],
            'subnet-id': subnet['id'],
        })
        org = Org.info({'id': org['id']})
        self.assertEqual(len(org['subnets']), 0)

    @tier2
    def test_positive_add_user_by_name(self):
        """Add an user to organization by its name

        @id: c35b2e88-a65f-4eea-ba55-89cef59f30be

        @Assert: User is added to the org

        @CaseLevel: Integration
        """
        org = make_org()
        user = make_user()
        Org.add_user({
            'name': org['name'],
            'user': user['login'],
        })
        org = Org.info({'name': org['name']})
        self.assertIn(user['login'], org['users'])

    @tier2
    def test_positive_add_user_by_id(self):
        """Add an user to organization by its ID

        @id: 1cd4e912-dd59-4cf7-b1a3-87b130972f8d

        @Assert: User is added to the org

        @CaseLevel: Integration
        """
        org = make_org()
        user = make_user()
        Org.add_user({
            'id': org['id'],
            'user-id': user['id'],
        })
        org = Org.info({'id': org['id']})
        self.assertIn(user['login'], org['users'])

    @tier2
    def test_positive_remove_user_by_id(self):
        """Remove an user from organization by its ID

        @id: 6e292d5f-3bce-48c5-88d7-2c94f7db51c1

        @Assert: The user is removed from the organization

        @CaseLevel: Integration
        """
        org = make_org()
        user = make_user()
        Org.add_user({
            'id': org['id'],
            'user-id': user['id'],
        })
        Org.remove_user({
            'id': org['id'],
            'user-id': user['id'],
        })
        org = Org.info({'id': org['id']})
        self.assertNotIn(user['login'], org['users'])

    @tier2
    def test_positive_remove_user_by_name(self):
        """Remove an user from organization by its login and organization name

        @id: 98cf1224-750a-449b-8807-638ef07a55e5

        @assert: The user is removed from the organization

        @CaseLevel: Integration
        """
        org = make_org()
        user = make_user()
        Org.add_user({
            'name': org['name'],
            'user': user['login'],
        })
        Org.remove_user({
            'name': org['name'],
            'user': user['login'],
        })
        org = Org.info({'name': org['name']})
        self.assertNotIn(user['login'], org['users'])

    @tier2
    def test_positive_add_admin_user_by_id(self):
        """Add an admin user to an organization by user ID and the organization
        ID

        @id: 176f1d07-c24c-481d-912e-045ec9cbfa67

        @assert: The user is added to the organization

        @CaseLevel: Integration
        """
        org = make_org()
        user = make_user({'admin': '1'})
        self.assertEqual(user['admin'], 'yes')
        Org.add_user({
            'id': org['id'],
            'user-id': user['id'],
        })
        org = Org.info({'id': org['id']})
        self.assertIn(user['login'], org['users'])

    @tier2
    def test_positive_add_admin_user_by_name(self):
        """Add an admin user to an organization by user login and the
        organization name

        @id: 31e9ceeb-1ae2-4c95-8b60-c5774e570476

        @assert: The user is added to the organization

        @CaseLevel: Integration
        """
        org = make_org()
        user = make_user({'admin': '1'})
        self.assertEqual(user['admin'], 'yes')
        Org.add_user({
            'name': org['name'],
            'user': user['login'],
        })
        org = Org.info({'name': org['name']})
        self.assertIn(user['login'], org['users'])

    @tier2
    def test_positive_remove_admin_user_by_id(self):
        """Remove an admin user from organization by user ID and the
        organization ID

        @id: 7ecfb7d0-35af-48ba-a460-70da81ade4bd

        @assert: The admin user is removed from the organization

        @CaseLevel: Integration
        """
        org = make_org()
        user = make_user({'admin': '1'})
        self.assertEqual(user['admin'], 'yes')
        Org.add_user({
            'id': org['id'],
            'user-id': user['id'],
        })
        Org.remove_user({
            'id': org['id'],
            'user-id': user['id'],
        })
        org = Org.info({'id': org['id']})
        self.assertNotIn(user['login'], org['users'])

    @tier2
    def test_positive_remove_admin_user_by_name(self):
        """Remove an admin user from organization by user login and the
        organization name

        @id: 41f0d3e6-3b4b-4a3e-b3d1-3126a10ed433

        @assert: The user is added then removed from the organization

        @CaseLevel: Integration
        """
        org = make_org()
        user = make_user({'admin': '1'})
        Org.add_user({
            'name': org['name'],
            'user': user['login'],
        })
        Org.remove_user({
            'name': org['name'],
            'user': user['login'],
        })
        org = Org.info({'name': org['name']})
        self.assertNotIn(user['login'], org['users'])

    @run_only_on('sat')
    @tier2
    def test_positive_add_hostgroup_by_id(self):
        """Add a hostgroup to organization by its ID

        @id: 4edbb371-fbb0-4918-b4ac-afa3ab30cee0

        @Assert: Hostgroup is added to the org

        @CaseLevel: Integration
        """
        org = make_org()
        hostgroup = make_hostgroup()
        Org.add_hostgroup({
            'hostgroup-id': hostgroup['id'],
            'id': org['id'],
        })
        org = Org.info({'id': org['id']})
        self.assertIn(hostgroup['name'], org['hostgroups'])

    @run_only_on('sat')
    @tier2
    def test_positive_add_hostgroup_by_name(self):
        """Add a hostgroup to organization by its name

        @id: 9cb2ef26-a98a-43a4-977c-d97c82509508

        @Assert: Hostgroup is added to the org

        @CaseLevel: Integration
        """
        org = make_org()
        hostgroup = make_hostgroup()
        Org.add_hostgroup({
            'hostgroup': hostgroup['name'],
            'name': org['name'],
        })
        org = Org.info({'name': org['name']})
        self.assertIn(hostgroup['name'], org['hostgroups'])

    @run_only_on('sat')
    @tier2
    def test_positive_remove_hostgroup_by_name(self):
        """Remove a hostgroup from an organization by its name

        @id: 8b2804c9-cefe-4a8a-b3a4-12ea131cdef0

        @Assert: Hostgroup is removed from the organization

        @CaseLevel: Integration
        """
        org = make_org()
        hostgroup = make_hostgroup()
        Org.add_hostgroup({
            'hostgroup': hostgroup['name'],
            'name': org['name'],
        })
        Org.remove_hostgroup({
            'hostgroup': hostgroup['name'],
            'name': org['name'],
        })
        org = Org.info({'name': org['name']})
        self.assertNotIn(hostgroup['name'], org['hostgroups'])

    @run_only_on('sat')
    @tier2
    def test_positive_remove_hostgroup_by_id(self):
        """Remove a hostgroup from an organization by its ID

        @id: 34e2c7c8-dc20-4709-a5a9-83c0dee9d84d

        @assert: Hostgroup is removed from the org

        @CaseLevel: Integration
        """
        org = make_org()
        hostgroup = make_hostgroup()
        Org.add_hostgroup({
            'hostgroup-id': hostgroup['id'],
            'id': org['id'],
        })
        Org.remove_hostgroup({
            'hostgroup-id': hostgroup['id'],
            'id': org['id'],
        })
        org = Org.info({'id': org['id']})
        self.assertNotIn(hostgroup['name'], org['hostgroups'])

    @run_only_on('sat')
    @tier2
    def test_positive_add_compresource_by_name(self):
        """Add a compute resource to organization by its name

        @id: 4bc1f281-ef8e-450b-8ef6-f8d11da5324f

        @Assert: Compute Resource is added to the org

        @CaseLevel: Integration
        """
        org = make_org()
        compute_res = make_compute_resource({
            'provider': FOREMAN_PROVIDERS['libvirt'],
            'url': u'qemu+ssh://root@{0}/system'.format(
                settings.compute_resources.libvirt_hostname
            )
        })
        Org.add_compute_resource({
            'compute-resource': compute_res['name'],
            'name': org['name'],
        })
        org = Org.info({'id': org['id']})
        self.assertEqual(org['compute-resources'][0], compute_res['name'])

    @tier2
    def test_positive_add_compresource_by_id(self):
        """Add a compute resource to organization by its ID

        @id: 355e20c5-ec04-49f7-a0ae-0864a3fe0f3f

        @Assert: Compute Resource is added to the org

        @CaseLevel: Integration
        """
        compute_res = make_compute_resource()
        org = make_org({'compute-resource-ids': compute_res['id']})
        self.assertEqual(len(org['compute-resources']), 1)
        self.assertEqual(org['compute-resources'][0], compute_res['name'])

    @tier2
    def test_positive_add_compresources_by_id(self):
        """Add multiple compute resources to organization by their IDs

        @id: 65846f05-583b-4914-ad0a-9251ca585af5

        @Assert: All compute resources are added to the org

        @CaseLevel: Integration
        """
        cr_amount = random.randint(3, 5)
        resources = [make_compute_resource() for _ in range(cr_amount)]
        org = make_org({
            'compute-resource-ids':
                [resource['id'] for resource in resources],
        })
        self.assertEqual(len(org['compute-resources']), cr_amount)
        for resource in resources:
            self.assertIn(resource['name'], org['compute-resources'])

    @run_only_on('sat')
    @tier2
    def test_positive_remove_compresource_by_id(self):
        """Remove a compute resource from organization by its ID

        @id: 415c14ab-f879-4ed8-9ba7-8af4ada2e277

        @Assert: Compute resource is removed from the org

        @CaseLevel: Integration
        """
        org = make_org()
        compute_res = make_compute_resource({
            'provider': FOREMAN_PROVIDERS['libvirt'],
            'url': u'qemu+ssh://root@{0}/system'.format(
                settings.compute_resources.libvirt_hostname
            )
        })
        Org.add_compute_resource({
            'compute-resource-id': compute_res['id'],
            'id': org['id'],
        })
        Org.remove_compute_resource({
            'compute-resource-id': compute_res['id'],
            'id': org['id'],
        })
        org = Org.info({'id': org['id']})
        self.assertNotIn(compute_res['name'], org['compute-resources'])

    @run_only_on('sat')
    @tier2
    def test_positive_remove_compresource_by_name(self):
        """Remove a compute resource from organization by its name

        @id: 1b1313a8-8326-4b33-8113-17c5cf0d4ffb

        @Assert: Compute resource is removed from the org

        @CaseLevel: Integration
        """
        org = make_org()
        compute_res = make_compute_resource({
            'provider': FOREMAN_PROVIDERS['libvirt'],
            'url': u'qemu+ssh://root@{0}/system'.format(
                settings.compute_resources.libvirt_hostname
            )
        })
        Org.add_compute_resource({
            'compute-resource': compute_res['name'],
            'name': org['name'],
        })
        Org.remove_compute_resource({
            'compute-resource': compute_res['name'],
            'name': org['name'],
        })
        org = Org.info({'name': org['name']})
        self.assertNotIn(compute_res['name'], org['compute-resources'])

    @run_only_on('sat')
    @tier2
    def test_positive_add_medium_by_id(self):
        """Add a medium to organization by its ID

        @id: c2943a81-c8f7-44c4-926b-388055d7c290

        @Assert: Medium is added to the org

        @CaseLevel: Integration
        """
        org = make_org()
        medium = make_medium()
        Org.add_medium({
            'id': org['id'],
            'medium-id': medium['id'],
        })
        org = Org.info({'id': org['id']})
        self.assertIn(medium['name'], org['installation-media'])

    @run_only_on('sat')
    @tier2
    def test_positive_add_medium_by_name(self):
        """Add a medium to organization by its name

        @id: dcbaf2bb-ebb9-4430-8584-08b4cad00ad5

        @Assert: Medium is added to the org

        @CaseLevel: Integration
        """
        org = make_org()
        medium = make_medium()
        Org.add_medium({
            'name': org['name'],
            'medium': medium['name'],
        })
        org = Org.info({'name': org['name']})
        self.assertIn(medium['name'], org['installation-media'])

    @run_only_on('sat')
    @tier2
    def test_positive_remove_medium_by_id(self):
        """Remove a medium from organization by its ID

        @id: 703103d8-f4d4-4070-bd6b-1fd239a92fa5

        @Assert: Medium is removed from the org

        @CaseLevel: Integration
        """
        org = make_org()
        medium = make_medium()
        Org.add_medium({
            'id': org['id'],
            'medium-id': medium['id'],
        })
        Org.remove_medium({
            'id': org['id'],
            'medium-id': medium['id'],
        })
        org = Org.info({'id': org['id']})
        self.assertNotIn(medium['name'], org['installation-media'])

    @run_only_on('sat')
    @tier2
    def test_positive_remove_medium_by_name(self):
        """Remove a medium from organization by its name

        @id: feb6c092-3459-496d-a403-69b540ba469a

        @Assert: Medium is removed from the org

        @CaseLevel: Integration
        """
        org = make_org()
        medium = make_medium()
        Org.add_medium({
            'name': org['name'],
            'medium': medium['name'],
        })
        Org.remove_medium({
            'name': org['name'],
            'medium': medium['name'],
        })
        org = Org.info({'id': org['id']})
        self.assertNotIn(medium['name'], org['installation-media'])

    @run_only_on('sat')
    @tier2
    def test_positive_add_template_by_name(self):
        """Add a provisioning template to organization by its name

        @id: bd46a192-488f-4da0-bf47-1f370ae5f55c

        @Assert: Template is added to the org

        @CaseLevel: Integration
        """
        for name in valid_data_list():
            with self.subTest(name):
                org = make_org()
                template = make_template({
                    'content': gen_string('alpha'),
                    'name': name,
                })
                Org.add_config_template({
                    'config-template': template['name'],
                    'name': org['name'],
                })
                org = Org.info({'name': org['name']})
                self.assertIn(
                    u'{0} ({1})'. format(template['name'], template['type']),
                    org['templates']
                )

    @tier2
    def test_positive_add_template_by_id(self):
        """Add a provisioning template to organization by its ID

        @id: 4dd119bf-e9e1-4c9a-9b6b-b2c1cc7bc015

        @Assert: Template is added to the org

        @CaseLevel: Integration
        """
        conf_templ = make_template()
        org = make_org()
        Org.add_config_template({
            'config-template-id': conf_templ['id'],
            'id': org['id'],
        })
        org = Org.info({'id': org['id']})
        self.assertIn(
            u'{0} ({1})'.format(conf_templ['name'], conf_templ['type']),
            org['templates']
        )

    @tier2
    def test_positive_add_templates_by_id(self):
        """Add multiple provisioning templates to organization by their IDs

        @id: 24cf7c8f-1e3b-4f37-b66d-24e6c125c752

        @Assert: All provisioning templates are added to the org

        @CaseLevel: Integration
        """
        templates_amount = random.randint(3, 5)
        templates = [make_template() for _ in range(templates_amount)]
        org = make_org({
            'config-template-ids':
                [template['id'] for template in templates],
        })
        self.assertGreaterEqual(len(org['templates']), templates_amount)
        for template in templates:
            self.assertIn(
                u'{0} ({1})'.format(template['name'], template['type']),
                org['templates']
            )

    @run_only_on('sat')
    @tier2
    def test_positive_remove_template_by_id(self):
        """Remove a provisioning template from organization by its ID

        @id: 8f3e05c2-6c0d-48a6-a311-41ad032b7977

        @Assert: Template is removed from the org

        @CaseLevel: Integration
        """
        org = make_org()
        template = make_template({'content': gen_string('alpha')})
        # Add config-template
        Org.add_config_template({
            'config-template-id': template['id'],
            'id': org['id'],
        })
        result = Org.info({'id': org['id']})
        self.assertIn(
            u'{0} ({1})'. format(template['name'], template['type']),
            result['templates'],
        )
        # Remove config-template
        Org.remove_config_template({
            'config-template-id': template['id'],
            'id': org['id'],
        })
        result = Org.info({'id': org['id']})
        self.assertNotIn(
            u'{0} ({1})'. format(template['name'], template['type']),
            result['templates'],
        )

    @run_only_on('sat')
    @tier2
    def test_positive_remove_template_by_name(self):
        """ARemove a provisioning template from organization by its name

        @id: 6db69282-8a0a-40cb-b494-8f555772ca81

        @Assert: Template is removed from the org

        @CaseLevel: Integration
        """
        for name in valid_data_list():
            with self.subTest(name):
                org = make_org()
                template = make_template({
                    'content': gen_string('alpha'),
                    'name': name,
                })
                # Add config-template
                Org.add_config_template({
                    'name': org['name'],
                    'config-template': template['name'],
                })
                result = Org.info({'name': org['name']})
                self.assertIn(
                    u'{0} ({1})'. format(template['name'], template['type']),
                    result['templates'],
                )
                # Remove config-template
                Org.remove_config_template({
                    'config-template': template['name'],
                    'name': org['name'],
                })
                result = Org.info({'name': org['name']})
                self.assertNotIn(
                    u'{0} ({1})'. format(template['name'], template['type']),
                    result['templates'],
                )

    @run_only_on('sat')
    @tier2
    def test_positive_add_domain_by_name(self):
        """Add a domain to organization by its name

        @id: 97359ffe-4ce6-4e44-9e3f-583d3fdebbc8

        @assert: Domain is added to organization

        @CaseLevel: Integration
        """
        org = make_org()
        domain = make_domain()
        Org.add_domain({
            'domain': domain['name'],
            'name': org['name'],
        })
        result = Org.info({'id': org['id']})
        self.assertEqual(len(result['domains']), 1)
        self.assertIn(domain['name'], result['domains'])

    @run_only_on('sat')
    @tier2
    def test_positive_add_domain_by_id(self):
        """Add a domain to organization by its ID

        @id: 33df2dc5-33ea-416d-bf13-f90aaf327e18

        @assert: Domain is added to organization

        @CaseLevel: Integration
        """
        org = make_org()
        domain = make_domain()
        Org.add_domain({
            'domain-id': domain['id'],
            'name': org['name'],
        })
        result = Org.info({'id': org['id']})
        self.assertEqual(len(result['domains']), 1)
        self.assertIn(domain['name'], result['domains'])

    @run_only_on('sat')
    @tier2
    def test_positive_remove_domain_by_name(self):
        """Remove a domain from organization by its name

        @id: 59ab55ab-782b-4ee2-b347-f1a1e37c55aa

        @Assert: Domain is removed from the org

        @CaseLevel: Integration
        """
        org = make_org()
        domain = make_domain()
        Org.add_domain({
            'domain': domain['name'],
            'name': org['name'],
        })
        result = Org.info({'id': org['id']})
        self.assertEqual(len(result['domains']), 1)
        self.assertIn(domain['name'], result['domains'])
        Org.remove_domain({
            'domain': domain['name'],
            'name': org['name'],
        })
        result = Org.info({'id': org['id']})
        self.assertEqual(len(result['domains']), 0)

    @run_only_on('sat')
    @tier2
    def test_positive_remove_domain_by_id(self):
        """Remove a domain from organization by its ID

        @id: 01ef8a26-e944-4cda-b60a-2b9d86a8051f

        @assert: Domain is removed from the organization

        @CaseLevel: Integration
        """
        org = make_org()
        domain = make_domain()
        Org.add_domain({
            'domain-id': domain['id'],
            'name': org['name'],
        })
        result = Org.info({'id': org['id']})
        self.assertEqual(len(result['domains']), 1)
        self.assertIn(domain['name'], result['domains'])
        Org.remove_domain({
            'domain-id': domain['id'],
            'id': org['id'],
        })
        result = Org.info({'id': org['id']})
        self.assertEqual(len(result['domains']), 0)

    @run_only_on('sat')
    @tier2
    def test_positive_add_lce(self):
        """Add a lifecycle environment to organization

        @id: 3620eeac-bf4e-4055-a6b4-4da10efbbfa2

        @Assert: Lifecycle environment is added to the org

        @CaseLevel: Integration
        """
        # Create a lifecycle environment.
        org_id = make_org()['id']
        lc_env_name = make_lifecycle_environment(
            {'organization-id': org_id})['name']
        # Read back information about the lifecycle environment. Verify the
        # sanity of that information.
        response = LifecycleEnvironment.list({
            'name': lc_env_name,
            'organization-id': org_id,
        })
        self.assertEqual(response[0]['name'], lc_env_name)

    @run_only_on('sat')
    @tier2
    def test_positive_remove_lce(self):
        """Remove a lifecycle environment from organization

        @id: bfa9198e-6078-4f10-b79a-3d7f51b835fd

        @Assert: Lifecycle environment is removed from the org

        @CaseLevel: Integration
        """
        # Create a lifecycle environment.
        org_id = make_org()['id']
        lc_env_name = make_lifecycle_environment(
            {'organization-id': org_id})['name']
        lc_env_attrs = {
            'name': lc_env_name,
            'organization-id': org_id,
        }
        # Read back information about the lifecycle environment. Verify the
        # sanity of that information.
        response = LifecycleEnvironment.list(lc_env_attrs)
        self.assertEqual(response[0]['name'], lc_env_name)
        # Delete it.
        LifecycleEnvironment.delete(lc_env_attrs)
        # We should get a zero-length response when searching for the LC env.
        response = LifecycleEnvironment.list(lc_env_attrs)
        self.assertEqual(len(response), 0)

    @run_only_on('sat')
    @tier2
    def test_positive_add_capsule_by_name(self):
        """Add a capsule to organization by its name

        @id: dbf9dd74-3b9e-4124-9468-b0eb978897df

        @Assert: Capsule is added to the org

        @CaseLevel: Integration
        """
        org = make_org()
        proxy = make_proxy()
        # Add capsule and org to cleanup list
        self.addCleanup(capsule_cleanup, proxy['id'])
        self.addCleanup(org_cleanup, org['id'])

        Org.add_smart_proxy({
            'name': org['name'],
            'smart-proxy': proxy['name'],
        })
        org = Org.info({'name': org['name']})
        self.assertIn(proxy['name'], org['smart-proxies'])

    @run_only_on('sat')
    @tier2
    def test_positive_add_capsule_by_id(self):
        """Add a capsule to organization by its ID

        @id: 0a64ebbe-d357-4ca8-b19e-86ea0963dc71

        @assert: Capsule is added to the org

        @CaseLevel: Integration
        """
        org = make_org()
        proxy = make_proxy()
        # Add capsule and org to cleanup list
        self.addCleanup(capsule_cleanup, proxy['id'])
        self.addCleanup(org_cleanup, org['id'])

        Org.add_smart_proxy({
            'name': org['name'],
            'smart-proxy-id': proxy['id'],
        })
        org = Org.info({'name': org['name']})
        self.assertIn(proxy['name'], org['smart-proxies'])

    @run_only_on('sat')
    @tier2
    def test_positive_remove_capsule_by_id(self):
        """Remove a capsule from organization by its id

        @id: 71af64ec-5cbb-4dd8-ba90-652e302305ec

        @Assert: Capsule is removed from the org

        @CaseLevel: Integration
        """
        org = make_org()
        proxy = make_proxy()
        # Add capsule and org to cleanup list
        self.addCleanup(capsule_cleanup, proxy['id'])
        self.addCleanup(org_cleanup, org['id'])

        Org.add_smart_proxy({
            'id': org['id'],
            'smart-proxy-id': proxy['id'],
        })
        Org.remove_smart_proxy({
            'id': org['id'],
            'smart-proxy-id': proxy['id'],
        })
        org = Org.info({'id': org['id']})
        self.assertNotIn(proxy['name'], org['smart-proxies'])

    @run_only_on('sat')
    @tier2
    def test_positive_remove_capsule_by_name(self):
        """Remove a capsule from organization by its name

        @id: f56eaf46-fef5-4b52-819f-e30e61f0ec4a

        @Assert: Capsule is removed from the org

        @CaseLevel: Integration
        """
        org = make_org()
        proxy = make_proxy()
        # Add capsule and org to cleanup list
        self.addCleanup(capsule_cleanup, proxy['id'])
        self.addCleanup(org_cleanup, org['id'])

        Org.add_smart_proxy({
            'name': org['name'],
            'smart-proxy': proxy['name'],
        })
        Org.remove_smart_proxy({
            'name': org['name'],
            'smart-proxy': proxy['name'],
        })
        org = Org.info({'name': org['name']})
        self.assertNotIn(proxy['name'], org['smart-proxies'])

    # Negative Create

    @tier1
    def test_negative_create_with_invalid_name(self):
        """Try to create an organization with invalid name, but valid label and
        description

        @id: f0aecf1e-d093-4365-af85-b3650ed21318

        @assert: organization is not created
        """
        for name in invalid_values_list():
            with self.subTest(name):
                with self.assertRaises(CLIReturnCodeError):
                    Org.create({
                        'description': gen_string('alpha'),
                        'label': gen_string('alpha'),
                        'name': name,
                    })

    @tier1
    def test_negative_create_same_name(self):
        """Create organization with valid values, then create a new one with
        same values

        @id: 07924e1f-1eff-4bae-b0db-e41b84966bc1

        @assert: organization is not created
        """
        for desc, name, label in zip(
                valid_data_list(),
                valid_org_names_list(),
                cycle(valid_labels_list()),
        ):
            with self.subTest(desc + name + label):
                Org.create({
                    'description': desc,
                    'label': label,
                    'name': name,
                })
                with self.assertRaises(CLIReturnCodeError):
                    Org.create({
                        'description': desc,
                        'label': label,
                        'name': name,
                    })

    # Positive Delete

    @tier1
    def test_positive_delete_by_id(self):
        """Delete an organization by ID

        @id: b1f5d246-2b12-4302-9824-00d3561f8699

        @assert: organization is deleted
        """
        org = make_org()
        Org.delete({'id': org['id']})
        # Can we find the object?
        with self.assertRaises(CLIReturnCodeError):
            Org.info({'id': org['id']})

    @tier1
    def test_positive_delete_by_label(self):
        """Delete an organization by label

        @id: 5624f318-ce10-4eaa-815b-0d6ec1e6b438

        @assert: organization is deleted
        """
        for label in valid_labels_list():
            with self.subTest(label):
                org = make_org({'label': label})
                Org.delete({'label': org['label']})
                # Can we find the object?
                with self.assertRaises(CLIReturnCodeError):
                    Org.info({'id': org['id']})

    @tier1
    def test_positive_delete_by_name(self):
        """Delete an organization by name

        @id: c2787b85-fa87-4aaf-bee4-4695249dd5d8

        @assert: organization is deleted
        """
        for name in valid_org_names_list():
            with self.subTest(name):
                org = make_org({'name': name})
                Org.delete({'name': org['name']})
                # Can we find the object?
                with self.assertRaises(CLIReturnCodeError):
                    Org.info({'id': org['id']})

    @tier1
    def test_positive_update_name(self):
        """Create organization with valid values then update its name

        @id: 66581003-f5d9-443c-8cd6-00f68087e8e9

        @assert: organization name is updated
        """
        for new_name in valid_org_names_list():
            with self.subTest(new_name):
                org = make_org()
                # Update the org name
                Org.update({
                    'id': org['id'],
                    'new-name': new_name,
                })
                # Fetch the org again
                org = Org.info({'id': org['id']})
                self.assertEqual(org['name'], new_name)

    @tier1
    def test_positive_update_description(self):
        """Create organization with valid values then update its description

        @id: c5cb0d68-10dd-48ee-8d56-83be8b33d729

        @assert: organization description is updated
        """
        for new_desc in valid_data_list():
            with self.subTest(new_desc):
                org = make_org()
                # Update the org name
                Org.update({
                    'description': new_desc,
                    'id': org['id'],
                })
                # Fetch the org again
                org = Org.info({'id': org['id']})
                self.assertEqual(org['description'], new_desc)

    @tier1
    def test_positive_update_name_description(self):
        """Create organization with valid values then update its name and
        description

        @id: 42635526-fb10-4811-8fe7-1d4c218a056e

        @assert: organization name and description are updated
        """
        for new_name, new_desc in zip(
                valid_org_names_list(), valid_data_list()):
            with self.subTest(new_name + new_desc):
                org = make_org()
                # Update the org name
                Org.update({
                    'description': new_desc,
                    'id': org['id'],
                    'new-name': new_name,
                })
                # Fetch the org again
                org = Org.info({'id': org['id']})
                self.assertEqual(org['description'], new_desc)
                self.assertEqual(org['name'], new_name)

    # Negative Update

    @tier1
    def test_negative_update_name(self):
        """Create organization then fail to update its name

        @id: 582d41b8-370d-45ed-9b7b-8096608e1324

        @assert: organization name is not updated
        """
        for new_name in invalid_values_list():
            with self.subTest(new_name):
                org = make_org()
                # Update the org name
                with self.assertRaises(CLIReturnCodeError):
                    Org.update({
                        'id': org['id'],
                        'new-name': new_name,
                    })

    # This test also covers the redmine bug 4443
    @tier1
    def test_positive_search_by_name(self):
        """Can search for an organization by name

        @id: 4279972b-180d-40ce-944f-47a1940af25d

        @assert: organization is created and can be searched by name
        """
        for name in valid_org_names_list():
            with self.subTest(name):
                org = make_org({'name': name})
                # Can we find the new object?
                result = Org.exists(search=('name', org['name']))
                self.assertEqual(org['name'], result['name'])

    @tier1
    def test_positive_search_by_label(self):
        """Can search for an organization by name

        @id: 0e5a23fa-86d2-4114-be39-0e6228c76f19

        @assert: organization is created and can be searched by label
        """
        for name in valid_org_names_list():
            with self.subTest(name):
                org = make_org({'name': name})
                # Can we find the new object?
                result = Org.exists(search=('label', org['label']))
                self.assertEqual(org['name'], result['name'])

    @tier1
    def test_positive_info_by_label(self):
        """Get org information by its label

        @id: 02328b67-5d24-4873-b716-113eee3ff67b

        @Assert: Organization is created and info can be obtained by its label
        graciously
        """
        org = make_org()
        result = Org.info({'label': org['label']})
        self.assertEqual(org['id'], result['id'])

    @tier1
    def test_positive_info_by_name(self):
        """Get org information by its name

        @id: cf971026-26a4-428f-b560-bb14e5324207

        @Assert: Organization is created and info can be obtained by its name
        graciously
        """
        org = make_org()
        result = Org.info({'name': org['name']})
        self.assertEqual(org['id'], result['id'])
