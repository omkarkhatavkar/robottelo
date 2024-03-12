"""Test class for Ansible Roles and Variables pages

:Requirement: Ansible

:CaseAutomation: Automated

:CaseLevel: Acceptance

:CaseComponent: Ansible-ConfigurationManagement

:Team: Rocket

:TestType: Functional

:CaseImportance: Critical

:Upstream: No
"""
from fauxfactory import gen_string
import pytest
import yaml

from robottelo import constants
from robottelo.config import robottelo_tmp_dir, settings


def test_positive_create_and_delete_variable(target_sat):
    """Create an Ansible variable with the minimum required values, then delete the variable.

    :id: 7006d7c7-788a-4447-a564-d6b03ec06aaf

    :Steps:

        1. Import Ansible roles if none have been imported yet.
        2. Create an Ansible variable with only a name and an assigned Ansible role.
        3. Verify that the Ansible variable has been created.
        4. Delete the Ansible variable.
        5. Verify that the Ansible Variable has been deleted.

    :expectedresults: The variable is successfully created and deleted.
    """
    key = gen_string('alpha')
    role = 'redhat.satellite.activation_keys'
    with target_sat.ui_session() as session:
        if not session.ansibleroles.imported_roles_count:
            session.ansibleroles.import_all_roles()
        session.ansiblevariables.create(
            {
                'key': key,
                'ansible_role': role,
            }
        )
        assert session.ansiblevariables.search(key)[0]['Name'] == key
        session.ansiblevariables.delete(key)
        assert not session.ansiblevariables.search(key)


def test_positive_create_variable_with_overrides(target_sat):
    """Create an Ansible variable with all values populated.

    :id: 90acea37-4c2f-42e5-92a6-0c88148f4fb6

    :Steps:

        1. Import Ansible roles if none have been imported yet.
        2. Create an Anible variable, populating all fields on the creation form.
        3. Verify that the Ansible variable was created successfully.

    :expectedresults: The variable is successfully created.
    """
    key = gen_string('alpha')
    role = 'redhat.satellite.activation_keys'
    with target_sat.ui_session() as session:
        if not session.ansibleroles.imported_roles_count:
            session.ansibleroles.import_all_roles()
        session.ansiblevariables.create_with_overrides(
            {
                'key': key,
                'description': 'this is a description',
                'ansible_role': role,
                'parameter_type': 'integer',
                'default_value': '11',
                'validator_type': 'list',
                'validator_rule': '11, 12, 13',
                'attribute_order': 'domain \n fqdn \n hostgroup \n os',
                'matcher_section.params': [
                    {
                        'attribute_type': {'matcher_key': 'os', 'matcher_value': 'fedora'},
                        'value': '13',
                    }
                ],
            }
        )
        assert session.ansiblevariables.search(key)[0]['Name'] == key


@pytest.mark.pit_server
@pytest.mark.no_containers
@pytest.mark.rhel_ver_match('[^6]')
def test_positive_config_report_ansible(session, target_sat, module_org, rhel_contenthost):
    """Test Config Report generation with Ansible Jobs.

    :id: 118e25e5-409e-44ba-b908-217da9722576

    :steps:
        1. Register a content host with satellite
        2. Import a role into satellite
        3. Assign that role to a host
        4. Assert that the role was assigned to the host successfully
        5. Run the Ansible playbook associated with that role
        6. Check if the report is created successfully

    :expectedresults:
        1. Host should be assigned the proper role.
        2. Job report should be created.

    :CaseComponent: Ansible-RemoteExecution
    """
    SELECTED_ROLE = 'RedHatInsights.insights-client'
    if rhel_contenthost.os_version.major <= 7:
        rhel_contenthost.create_custom_repos(rhel7=settings.repos.rhel7_os)
        assert rhel_contenthost.execute('yum install -y insights-client').status == 0
    rhel_contenthost.install_katello_ca(target_sat)
    rhel_contenthost.register_contenthost(module_org.label, force=True)
    assert rhel_contenthost.subscribed
    rhel_contenthost.add_rex_key(satellite=target_sat)
    id = target_sat.nailgun_smart_proxy.id
    target_host = rhel_contenthost.nailgun_host
    target_sat.api.AnsibleRoles().sync(data={'proxy_id': id, 'role_names': [SELECTED_ROLE]})
    target_sat.cli.Host.ansible_roles_assign({'id': target_host.id, 'ansible-roles': SELECTED_ROLE})
    host_roles = target_host.list_ansible_roles()
    assert host_roles[0]['name'] == SELECTED_ROLE
    template_id = (
        target_sat.api.JobTemplate()
        .search(query={'search': 'name="Ansible Roles - Ansible Default"'})[0]
        .id
    )
    job = target_sat.api.JobInvocation().run(
        synchronous=False,
        data={
            'job_template_id': template_id,
            'targeting_type': 'static_query',
            'search_query': f'name = {rhel_contenthost.hostname}',
        },
    )
    target_sat.wait_for_tasks(
        f'resource_type = JobInvocation and resource_id = {job["id"]}', poll_timeout=1000
    )
    result = target_sat.api.JobInvocation(id=job['id']).read()
    assert result.succeeded == 1
    with session:
        session.location.select(constants.DEFAULT_LOC)
        assert session.host.search(target_host.name)[0]['Name'] == rhel_contenthost.hostname
        session.configreport.search(rhel_contenthost.hostname)
        session.configreport.delete(rhel_contenthost.hostname)
        assert len(session.configreport.read()['table']) == 0


@pytest.mark.no_containers
@pytest.mark.rhel_ver_match('9')
def test_positive_ansible_custom_role(target_sat, session, module_org, rhel_contenthost, request):
    """
    Test Config report generation with Custom Ansible Role

    :id: 3551068a-ccfc-481c-b7ec-8fe2b8a802bf

    :customerscenario: true

    :Steps:
        1. Register a content host with satellite
        2. Create a  custom role and import  into satellite
        3. Assign that role to a host
        4. Assert that the role was assigned to the host successfully
        5. Run the Ansible playbook associated with that role
        6. Check if the report is created successfully

    :expectedresults:
        1. Config report should be generated for a custom role run.

    :BZ: 2155392

    :CaseComponent: Ansible-RemoteExecution
    """
    SELECTED_ROLE = 'custom_role'
    playbook = f'{robottelo_tmp_dir}/playbook.yml'
    data = {
        'name': 'Copy ssh keys',
        'copy': {
            'src': '/var/lib/foreman-proxy/ssh/{{ item }}',
            'dest': '/root/.ssh',
            'owner': 'root',
            "group": 'root',
            'mode': '0400',
        },
        'with_items': ['id_rsa_foreman_proxy.pub', 'id_rsa_foreman_proxy'],
    }
    with open(playbook, 'w') as f:
        yaml.dump(data, f, sort_keys=False, default_flow_style=False)
    target_sat.execute('mkdir /etc/ansible/roles/custom_role')
    target_sat.put(playbook, '/etc/ansible/roles/custom_role/playbook.yaml')
    rhel_contenthost.install_katello_ca(target_sat)
    rhel_contenthost.register_contenthost(module_org.label, force=True)
    assert rhel_contenthost.subscribed
    rhel_contenthost.add_rex_key(satellite=target_sat)
    proxy_id = target_sat.nailgun_smart_proxy.id
    target_host = rhel_contenthost.nailgun_host
    target_sat.api.AnsibleRoles().sync(data={'proxy_id': proxy_id, 'role_names': [SELECTED_ROLE]})
    target_sat.cli.Host.ansible_roles_assign({'id': target_host.id, 'ansible-roles': SELECTED_ROLE})
    host_roles = target_host.list_ansible_roles()
    assert host_roles[0]['name'] == SELECTED_ROLE

    template_id = (
        target_sat.api.JobTemplate()
        .search(query={'search': 'name="Ansible Roles - Ansible Default"'})[0]
        .id
    )
    job = target_sat.api.JobInvocation().run(
        synchronous=False,
        data={
            'job_template_id': template_id,
            'targeting_type': 'static_query',
            'search_query': f'name = {rhel_contenthost.hostname}',
        },
    )
    target_sat.wait_for_tasks(
        f'resource_type = JobInvocation and resource_id = {job["id"]}', poll_timeout=1000
    )
    result = target_sat.api.JobInvocation(id=job['id']).read()
    assert result.succeeded == 1
    with session:
        session.location.select(constants.DEFAULT_LOC)
        assert session.host.search(target_host.name)[0]['Name'] == rhel_contenthost.hostname
        session.configreport.search(rhel_contenthost.hostname)
        session.configreport.delete(rhel_contenthost.hostname)
        assert len(session.configreport.read()['table']) == 0

    @request.addfinalizer
    def _finalize():
        result = target_sat.cli.Ansible.roles_delete({'name': SELECTED_ROLE})
        assert f'Ansible role [{SELECTED_ROLE}] was deleted.' in result[0]['message']
        target_sat.execute('rm -rvf /etc/ansible/roles/custom_role')
